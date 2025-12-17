import os
import json
import pandas as pd
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()

# Dossiers
DOSSIER_INPUT = "factures_a_traiter"
DOSSIER_OUTPUT = "factures_traitees"
FICHIER_CSV_APP = "rapport_depenses.csv"
FICHIER_CSV_MAIN = "compilation.csv"

# Config Gemini
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- CORE FUNCTIONS ---

def get_prompt():
    """Returns the prompt for the Gemini API."""
    return """
    Analyse cette image de facture. Extrais : date (YYYY-MM-DD), vendeur, total (nombre), devise.
    Retourne un JSON. Si illisible, mets null.
    """

def analyser_image_gemini(image_path, prompt):
    """Sends the image to Gemini and returns the JSON."""
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("❌ Clé API manquante dans le fichier .env")

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )
    try:
        image = Image.open(image_path)
        response = model.generate_content([prompt, image])
        return json.loads(response.text)
    except Exception as e:
        print(f"Erreur sur {os.path.basename(image_path)}: {e}")
        return None

def get_files(folder):
    """Gets the list of images in a folder."""
    return [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

def process_invoices(is_streamlit_app=False):
    """
    Processes invoices from the input folder, analyzes them, renames and moves them,
    and generates a CSV report.
    """
    files_input = get_files(DOSSIER_INPUT)
    if not files_input:
        if is_streamlit_app:
            return "Le dossier est vide. Déposez des images dans 'factures_a_traiter'.", None
        else:
            return "⚠️ Veuillez ajouter des images dans le dossier '{DOSSIER_INPUT}' pour que le script fonctionne", None

    resultats_session = []
    prompt = get_prompt()

    for i, fichier in enumerate(files_input):
        chemin_complet = os.path.join(DOSSIER_INPUT, fichier)
        
        if is_streamlit_app:
            # In a real app, you'd use a more robust way to pass progress
            print(f"Analyse en cours : {fichier}...")

        donnees = analyser_image_gemini(chemin_complet, prompt)
        
        if donnees:
            vendeur_clean = "".join(x for x in str(donnees.get('vendeur')) if x.isalnum())
            date_clean = donnees.get('date', 'inconnue')
            nouveau_nom = f"{date_clean}_{vendeur_clean}_{donnees.get('total')}.jpg"
            chemin_destination = os.path.join(DOSSIER_OUTPUT, nouveau_nom)
            
            os.rename(chemin_complet, chemin_destination)
            
            donnees['fichier_original'] = fichier
            donnees['fichier_final'] = nouveau_nom
            resultats_session.append(donnees)

    if resultats_session:
        new_df = pd.DataFrame(resultats_session)
        
        fichier_csv = FICHIER_CSV_APP if is_streamlit_app else FICHIER_CSV_MAIN

        if os.path.exists(fichier_csv):
            old_df = pd.read_csv(fichier_csv)
            final_df = pd.concat([old_df, new_df], ignore_index=True)
        else:
            final_df = new_df
            
        final_df.to_csv(fichier_csv, index=False)
        
        if is_streamlit_app:
            return f"Traitement terminé avec succès ! {len(resultats_session)} factures traitées.", final_df
        else:
            return f"🎉 Terminé ! Compilation généré : {fichier_csv}", final_df
            
    return "Aucune facture n'a pu être traitée.", None

