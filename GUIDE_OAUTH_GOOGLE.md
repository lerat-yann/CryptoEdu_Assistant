# Intégration OAuth Google — Guide de mise en place

## Fichiers modifiés / créés

### Nouveau : `google_oauth.py`
Module complet qui encapsule toute la logique OAuth + Gmail + Google Docs.
- **OAuth2** via `streamlit-oauth` (composant tiers qui donne un vrai access_token)
- **Gmail API** : envoi d'emails HTML formatés style CryptoEdu
- **Google Docs API** : création de documents dans le Drive de l'utilisateur
- **Widget sidebar** : bouton connexion/déconnexion avec affichage du profil

### Modifié : `app.py`
Changements apportés (Jour 6) :
1. **Import** de `google_oauth` (6 fonctions)
2. **Sidebar** : bloc "Compte Google" ajouté entre Notes/Tâches et Stack technique
3. **Bouton 💾** : dual mode — Google Docs si connecté, Markdown local sinon
   - Label change dynamiquement : "💾 Google Docs" vs "💾 Sauvegarder"
   - Message discret pour inciter à se connecter quand pas connecté
4. **Bouton 📧** (nouveau) : envoie la conversation complète par email Gmail
   - N'apparaît que si l'utilisateur est connecté Google
   - Confirmation avec affichage de l'email destinataire

### Fichier template : `secrets.toml.example`
Ajout des 3 clés Google :
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`  
- `GOOGLE_REDIRECT_URI`

---

## Étapes pour activer l'intégration

### 1. Ajouter la dépendance
Dans votre `requirements.txt`, ajoutez :
```
streamlit-oauth>=0.1.14
```

### 2. Ajouter `google_oauth.py` à la racine du projet
Placez le fichier à côté de `app.py`, `config.py`, etc.

### 3. Remplacer `app.py`
Remplacez l'ancien `app.py` par la nouvelle version.

### 4. Configurer les secrets

#### En local (`.env` ou `.streamlit/secrets.toml`)
```
GOOGLE_CLIENT_ID=xxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:8501
```

#### Sur Streamlit Cloud (Settings > Secrets)
```
GOOGLE_CLIENT_ID = "xxxxxxxxxxxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "GOCSPX-xxxxxxxxxxxx"
GOOGLE_REDIRECT_URI = "https://cryptoeduassistant-pmwwyo8ny659behdtaou8g.streamlit.app"
```

### 5. Vérifier les URIs de redirection dans Google Cloud Console
Dans **APIs & Services > Credentials > Votre Client OAuth** :
- `http://localhost:8501` (dev local)
- `https://cryptoeduassistant-pmwwyo8ny659behdtaou8g.streamlit.app` (production)

**Important** : pas de `/oauth2callback` à la fin — `streamlit-oauth` gère le callback différemment de `st.login()`.

### 6. Ajouter les testeurs (mode Test)
Tant que l'app OAuth est en mode "Test" dans Google Cloud :
- Allez dans **OAuth consent screen > Test users**
- Ajoutez chaque email Google qui doit pouvoir se connecter

---

## Comportement selon l'état de connexion

| Action | Non connecté Google | Connecté Google |
|--------|-------------------|-----------------|
| 💾 Sauvegarder | Note Markdown locale | Google Doc dans le Drive |
| ✅ Tâche | Inchangé (JSON local) | Inchangé (JSON local) |
| 🧠 Quiz | Inchangé | Inchangé |
| 📧 Email | Bouton masqué | Envoi via Gmail |
| Sidebar | Bouton "Se connecter avec Google" | Photo + nom + email + Déconnexion |

---

## Architecture OAuth — Comment ça marche

```
Utilisateur clique "Se connecter avec Google"
        │
        ▼
streamlit-oauth → redirige vers accounts.google.com
        │
        ▼
Google montre l'écran de consentement (scopes)
        │
        ▼
Utilisateur accepte → Google renvoie un code
        │
        ▼
streamlit-oauth échange le code contre un access_token
        │
        ▼
Token stocké dans st.session_state.google_token
        │
        ├──► Gmail API (envoi d'emails)
        ├──► Google Docs API (création de documents)
        └──► Google Userinfo (nom, email, photo)
```

---

## Notes techniques

- **Pourquoi `streamlit-oauth` et pas `st.login()` natif ?**
  `st.login()` utilise OIDC (OpenID Connect) qui donne uniquement l'identité de l'utilisateur. Il ne fournit PAS d'access_token pour agir au nom de l'utilisateur. Or, on a besoin d'envoyer des emails et créer des docs — ce qui nécessite un vrai token OAuth2 avec les bons scopes.

- **Fallback gracieux** : si `GOOGLE_CLIENT_ID` n'est pas défini, tout le bloc Google est simplement masqué. L'app fonctionne exactement comme avant.

- **Pas de refresh token automatique** : si le token expire (après ~1h), l'utilisateur devra se reconnecter. C'est acceptable pour un usage éducatif. On demande `access_type=offline` + `prompt=consent` pour obtenir un refresh_token, mais le refresh automatique pourra être ajouté plus tard si nécessaire.
