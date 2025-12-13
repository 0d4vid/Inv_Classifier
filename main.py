import os
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

#structure
DOSSIER_INPUT = "facture_a_traiter"
DOSSIER_OUTPUT = "factures_traitees"
FICHIER_CSV = "compilation.csv"

os.makedirs(DOSSIER_INPUT, exist_ok=True)
os.makedirs(DOSSIER_OUTPUT, exist_ok=True)

def analyse(path):
    print(f"👀 Le model IA analyse : {os.path.basename(path)}...")
    image = Image.open(path)

    #prompt
    prompt = """
    Analyse cette image de facture. Extrais les informations suivantes au format JSON :
    - date (format DD-MM-YYY)
    - vendeur (nom du commerce)
    - total (montant numerique uniquement)
    - devise (symbole ou code)
    Si une info est illisible, met null.
    """

    #configuration du model
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    try:
        response = model.generate_content([prompt, image])
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Erreur Gemini : {e}")
        return None
    
def main():
    print("Demarrage de l'assistant Comptable[AI]....")

    #liste des fichiers images
    fichiers = [f for f in os.listdir(DOSSIER_INPUT) if f.lower().endswith(('.png', 'jpg', 'jpeg', '.webp'))]

    if not fichiers:
        print(f"⚠️ Veuillez ajouter des images dans le dossier '{DOSSIER_INPUT}' pour que le script fonctionne")
        return
    resultats =[]

    for fichier in fichiers:
        full_path = os.path.join(DOSSIER_INPUT, fichier)

        data = analyse(full_path)

        if data:
            print(f"    ✅ Trouvé : {data.get('vendeur')} | {data.get('total')} {data.get('devise')}")

            vendeur_clean = "".join(x for x in str(data.get('vendeur')) if x.isalnum())
            date_clean = data.get('date', 'date-inconnue')

            nouveau_nom = f"{date_clean}_{vendeur_clean}_{data.get('total')}.jpg"
            destination = os.path.join(DOSSIER_OUTPUT, nouveau_nom)

            os.rename(full_path, destination)
            print(f"   📂 Fichier deplace vers : {nouveau_nom}\n")

            data['origina_file'] = fichier
            data['final_file'] = nouveau_nom
            resultats.append(data)

    #Redaction de la compilation
    if resultats:
        df = pd.DataFrame(resultats)
        cols = ['date', 'vendeur', 'total', 'devise', 'fichier_original', 'fichier_final']
        df = df[[c for c in cols if c in df.columns]]

        df.to_csv(FICHIER_CSV, index=False)
        print(f"🎉 Terminé ! Compilation généré : {FICHIER_CSV}")

if __name__ ==  "__main__":
    main()
    