# GitHub Setup for Students

## Create the account

1. Visit <https://github.com/signup> and use a professional email address.
2. Select a professional username; avoid birth dates and informal nicknames.
3. Enable two-factor authentication and save the recovery codes securely.
4. Add your full name, institution and a short technical bio to the profile.

## Configure Git once

```bash
git config --global user.name "Your Full Name"
git config --global user.email "your-email@example.com"
git config --global init.defaultBranch main
```

## Publish this local repository

Create an empty GitHub repository named `beyond-big-o-research`. Do not add a README or licence online because they already exist locally. Then run:

```bash
git init
git add .
git commit -m "Initial reproducible benchmark framework"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/beyond-big-o-research.git
git push -u origin main
```

## Student workflow

```bash
git checkout -b feature/short-description
git add path/to/changed-file
git commit -m "Explain the change clearly"
git push -u origin feature/short-description
```

Open a pull request, request review and merge only after automated checks pass. Never commit passwords, tokens, personal datasets, compiled binaries or manually edited results.

