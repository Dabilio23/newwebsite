# Dabilio — Site Web Officiel

Site vitrine de [Dabilio](https://dabil.io), plateforme de gestion scolaire pour les établissements d'enseignement à Madagascar.

## Structure du projet

```
.
├── index.html              # Page d'accueil
├── send.php                # Backend d'envoi d'emails (API Resend)
├── .htaccess               # Sécurité serveur Apache
├── modules/
│   ├── admission.html      # Module Admission
│   ├── annuaire.html       # Module Annuaire scolaire
│   └── services.html       # Services Dabilio
├── solutions/
│   ├── ecoles.html         # Solution pour les écoles
│   ├── universite.html     # Solution pour les universités
│   └── centre.html         # Solution pour les centres de formation
└── public/                 # Images et assets
```

## Stack technique

- **Frontend** — HTML5, Tailwind CSS (CDN), Iconify
- **Backend** — PHP (send.php) avec l'API [Resend](https://resend.com) pour l'envoi d'emails
- **Hébergement** — Infomaniak (Apache)

## Configuration

Les formulaires envoient les données à `send.php` qui relaie vers `marketing@dabil.io` via l'API Resend.

### Variable d'environnement requise

```
RESEND_API_KEY=your_api_key
```

La clé peut être définie via une variable d'environnement serveur ou un fichier `.env` à la racine (non versionné).

## Lancer en local

Pour tester les pages statiques :

```bash
python3 -m http.server 8080
```

Pour tester les formulaires (PHP requis) :

```bash
php -S localhost:8080
```

Puis ouvrir [http://localhost:8080](http://localhost:8080).

> Les formulaires nécessitent un serveur PHP et une clé `RESEND_API_KEY` valide pour fonctionner.

## Déploiement

Pousser sur la branche `main` :

```bash
git push origin main
```

Le dépôt distant est : `https://github.com/Dabilio23/newwebsite`
