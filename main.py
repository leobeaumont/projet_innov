from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Optional

class UserProfile(BaseModel):
    uname: Optional[str] = Field(description="Nom de l'utilisateur", default=None)
    uage: Optional[int] = Field(description="Age de l'utilisateur", default=None)
    uweight: Optional[int] = Field(description="Poids de l'utilisateur en kg", default=None)
    uheight: Optional[int] = Field(description="Taille de l'utilisateur en cm", default=None)
    ugoal: Optional[str] = Field(description="Objectif de l'utilisateur (prendre du muscle, perdre du poids...)", default=None)

class DailyIntake(BaseModel):
    kcal: Optional[int] = Field(description="Calories consommées dans la journée en kcal", default=None)
    prot: Optional[int] = Field(description="Protéines consommées dans la journée en g", default=None)
    glucides: Optional[int] = Field(description="Glucides consommées dans la journée en g", default=None)
    lipides: Optional[int] = Field(description="Lipides consommées dans la journée en g", default=None)
    eau: Optional[int] = Field(description="Eau consommées dans la journée en L", default=None)

class DailyActivity(BaseModel):
    kcal: Optional[int] = Field(description="Calories dépensées dans la journée en kcal", default=None)

# Chargement de la clé API google
load_dotenv()

# Initialisation du modèle
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.7,
    max_retries=2, 
)
structured_llm1 = llm.with_structured_output(UserProfile)
structured_llm2 = llm.with_structured_output(DailyIntake)
structured_llm3 = llm.with_structured_output(DailyActivity)


# Prompts
prompt1 = ChatPromptTemplate.from_messages([
    (
        "system", 
        "Tu es un assistant spécialisé en {domaine}. "
        "Tu dois extraire les informations de l'utilisateur de manière précise."
    ),
    ("user", "{question}")
])

prompt2 = ChatPromptTemplate.from_messages([
    (
        "system", 
        "Tu es un assistant spécialisé en {domaine}. "
        "Tu dois extraire les informations de l'utilisateur de manière précise."
        "L'utilisateur va te décrire tout ce qu'il a mangé et bu aujourd'hui."
        "Ton objectif est d'estimer à partir de ses consommation la quantité de calories, de protéines, de glucides, de lipides et d'eau qu'il a consommé."
        "Tu n'as pas besoins d'être très précis, mais plus tu donnes un résultat bon, meilleur sera la réponse."
    ),
    ("user", "{question}")
])

prompt3 = ChatPromptTemplate.from_messages([
    (
        "system", 
        "Tu es un assistant spécialisé en {domaine}. "
        "Tu dois extraire les informations de l'utilisateur de manière précise."
        "L'utilisateur va te décrire tout les activités physiques qu'il a fait aujourd'hui."
        "Ton objectif est d'estimer à partir de son activité la quantité de calories qu'il a dépensé."
        "Tu n'as pas besoins d'être très précis, mais plus tu donnes un résultat bon, meilleur sera la réponse."
    ),
    ("user", "{question}")
])

prompt_coach = ChatPromptTemplate.from_messages([
    (
        "system", 
        "Tu es un coach expert en nutrition et sport. "
        "Ton rôle est d'analyser le profil, la consommation et l'activité de l'utilisateur pour lui donner un conseil personnalisé."
    ),
    (
        "user", 
        "Voici les données du jour :\n"
        "- Profil: {profil}\n"
        "- Consommation: {conso}\n"
        "- Activité: {activite}\n\n"
        "Donne-moi une analyse rapide (points positifs et axes d'amélioration) et un conseil concret pour demain."
    )
])

# Construction chaine
chain1 = prompt1 | structured_llm1
chain2 = prompt2 | structured_llm2
chain3 = prompt3 | structured_llm3
chain_coach = prompt_coach | llm

# Exécution du script
try:
    print("Bonjour je suis votre assistant perso.\nCommencez par me décrire un peu votre profil. Donnez moi les informations suivantes:\n- Nom d'utilisateur\n- Votre age\n- Votre taille\n- Votre poids\n- Votre objectif (perdre du poids / prendre du muscle...)")
    user_input = input("Entrez votre réponse:")
    response1 = chain1.invoke({
        "domaine": "nutrition et sports",
        "question": user_input
    })

    print(f"\n\nTrès bien {response1.uname}. Maintenant décrivez moi avec précision tout ce que vous avez mangé et bu aujourd'hui.")
    user_input = input("Entrez votre réponse:")
    response2 = chain2.invoke({
        "domaine": "nutrition et sports",
        "question": user_input
    })

    print(f"\n\nD'accord {response1.uname}. Maintenant décrivez moi avec précision toute activité physique que vous avez fait aujourd'hui.")
    user_input = input("Entrez votre réponse:")
    response3 = chain3.invoke({
        "domaine": "nutrition et sports",
        "question": user_input
    })

    print("\n" + "="*40)
    print(f"RÉSUMÉ QUOTIDIEN POUR {response1.uname or 'Utilisateur'}")
    print("="*40)

    print(f"\nPROFIL :")
    print(f"- Objectif : {response1.ugoal or 'Non précisé'}")
    print(f"- Physique : {response1.uheight or '??'} cm | {response1.uweight or '??'} kg")

    print(f"\nCONSOMMATION ESTIMÉE :")
    print(f"- Énergie   : {response2.kcal or 0} kcal")
    print(f"- Protéines : {response2.prot or 0} g")
    print(f"- Glucides  : {response2.glucides or 0} g")
    print(f"- Lipides   : {response2.lipides or 0} g")
    print(f"- Eau       : {response2.eau or 0} L")

    print(f"\nACTIVITÉ PHYSIQUE :")
    print(f"- Calories dépensées : {response3.kcal or 0} kcal")

    if response2.kcal is not None and response3.kcal is not None:
        bilan = response2.kcal - response3.kcal
        print(f"\nBILAN ÉNERGÉTIQUE : {bilan} kcal")
    
    print("\n" + "="*40)

    print("Le coach réfléchis...")

    response_coach = chain_coach.invoke({
        "profil": response1.model_dump_json(),
        "conso": response2.model_dump_json(),
        "activite": response3.model_dump_json()
    })

    print("\nCONSEIL DE VOTRE COACH :")
    print("-" * 30)
    print(response_coach.content)
    print("-" * 30)

except Exception as e:
    print(f"Une erreur est survenue : {e}")
