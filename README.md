# Portalia - Simulateur de Salaire

Portalia est une application web permettant de simuler un salaire en fonction de plusieurs paramètres. Le projet est divisé en deux parties :

- **Frontend** : Développé avec Angular
- **Backend** : Développé avec FastAPI (Python)

## Installation et Lancement
1. Cloner le projet
    ```bash
    git clone <URL_DU_REPO>
    cd Portalia
    ```

2. Lancer le Frontend (Angular)
    ```bash
    cd Portalia
    npm install
    ng serve
    ```
    L'application Angular sera accessible sur : [http://localhost:4200/](http://localhost:4200/)

3. Lancer le Backend (FastAPI)
    ```bash
    cd Portalia/portalia
    pip install -r requirements.txt
    python -m uvicorn main:app --reload
    ```
    Le serveur FastAPI sera accessible sur : [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

⚠️ **Note** : Si une erreur se produit lors de l'installation des dépendances Python, essayez de commenter la dernière ligne du fichier `requirements.txt`.

## Technologies utilisées
- **Frontend** : Angular, TypeScript, HTML, CSS
- **Backend** : FastAPI, Python
- **Base de données** : (à préciser si applicable)

## Contribution
1. Forker le projet
2. Créer une branche : 
    ```bash
    git checkout -b feature-nom
    ```
3. Apporter vos modifications et commit : 
    ```bash
    git commit -m "Ajout d'une nouvelle fonctionnalité"
    ```
4. Pousser la branche : 
    ```bash
    git push origin feature-nom
    ```
5. Ouvrir une Pull Request

## Auteur
Projet développé par l'équipe Portalia 🚀