import streamlit as st
import os
import json
import pandas as pd
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()

# Configuration de la page (Doit être la première commande Streamlit)
st.set_page_config(page_title="Agent Compta IA", page_icon="🤖", layout="wide")

# Dossiers
DOSSIER_INPUT = "factures_a_traiter"
DOSSIER_OUTPUT = "factures_traitees"
FICHIER_CSV = "rapport_depenses.csv"

# Création des dossiers si inexistants
os.makedirs(DOSSIER_INPUT, exist_ok=True)
os.makedirs(DOSSIER_OUTPUT, exist_ok=True)

# Config Gemini
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
else:
    st.error("❌ Clé API manquante dans le fichier .env")

# --- FONCTIONS (Mêmes qu'avant, légèrement adaptées) ---

def analyser_image_gemini(image_path):
    """Envoie l'image à Gemini et retourne le JSON."""
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )
    prompt = """
    Analyse cette image de facture. Extrais : date (YYYY-MM-DD), vendeur, total (nombre), devise.
    Retourne un JSON. Si illisible, mets null.
    """
    try:
        image = Image.open(image_path)
        response = model.generate_content([prompt, image])
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Erreur sur {os.path.basename(image_path)}: {e}")
        return None

def get_files(folder):
    """Récupère la liste des images dans un dossier."""
    return [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

# --- INTERFACE STREAMLIT ---

st.title("🤖 Agent d'Automatisation Comptable")
st.markdown("Ce tableau de bord pilote un **agent IA** qui scanne, analyse et classe vos factures locales.")

col1, col2 = st.columns(2)

# COLONNE 1 : Zone d'entrée (Ce qu'il y a à faire)
with col1:
    st.subheader(f"📂 Dossier Entrant ({DOSSIER_INPUT})")
    files_input = get_files(DOSSIER_INPUT)
    
    if not files_input:
        st.info("Le dossier est vide. Déposez des images dans 'factures_a_traiter'.")
    else:
        st.write(f"**{len(files_input)} documents en attente.**")
        # Petite galerie pour voir ce qu'il y a à traiter
        for f in files_input[:3]: # Montre juste les 3 premiers pour pas encombrer
            st.image(os.path.join(DOSSIER_INPUT, f), width=150, caption=f)

# COLONNE 2 : Zone de sortie (Ce qui est fait)
with col2:
    st.subheader(f"✅ Dossier Traité ({DOSSIER_OUTPUT})")
    files_output = get_files(DOSSIER_OUTPUT)
    st.write(f"**{len(files_output)} documents archivés.**")
    if os.path.exists(FICHIER_CSV):
        df = pd.read_csv(FICHIER_CSV)
        st.dataframe(df.tail(5), hide_index=True) # Affiche les 5 dernières lignes

st.divider()

# --- LE BOUTON D'ACTION ---

if st.button("🚀 LANCER L'AGENT IA", type="primary", disabled=len(files_input)==0):
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    resultats_session = []

    # On boucle sur les fichiers
    for i, fichier in enumerate(files_input):
        chemin_complet = os.path.join(DOSSIER_INPUT, fichier)
        
        # 1. Update UI
        status_text.markdown(f"**Analyse en cours :** `{fichier}`...")
        
        # 2. Appel IA
        donnees = analyser_image_gemini(chemin_complet)
        
        if donnees:
            # 3. Traitement Local (Renommage)
            vendeur_clean = "".join(x for x in str(donnees.get('vendeur')) if x.isalnum())
            date_clean = donnees.get('date', 'inconnue')
            nouveau_nom = f"{date_clean}_{vendeur_clean}_{donnees.get('total')}.jpg"
            chemin_destination = os.path.join(DOSSIER_OUTPUT, nouveau_nom)
            
            os.rename(chemin_complet, chemin_destination)
            
            # Stockage pour le CSV
            donnees['fichier_original'] = fichier
            donnees['fichier_final'] = nouveau_nom
            resultats_session.append(donnees)
        
        # Update barre de progression
        progress_bar.progress((i + 1) / len(files_input))

    # 4. Finalisation
    if resultats_session:
        # Mise à jour du CSV global
        new_df = pd.DataFrame(resultats_session)
        if os.path.exists(FICHIER_CSV):
            old_df = pd.read_csv(FICHIER_CSV)
            final_df = pd.concat([old_df, new_df], ignore_index=True)
        else:
            final_df = new_df
            
        final_df.to_csv(FICHIER_CSV, index=False)
        
        status_text.success("✨ Traitement terminé avec succès !")
        st.balloons() # Petit effet sympa pour la fin
        
        # Bouton pour rafraîchir la page et voir les changements
        st.rerun()