# Push the project to a private GitHub repository

Do this once. Everything runs on your laptop; you sign in to GitHub yourself.

## 1. Create the empty repository on GitHub
1. Go to https://github.com/new and sign in.
2. Repository name: `voron-diagnostic-assistant` (or any name).
3. Choose **Private**.
4. Do NOT tick "Add a README", ".gitignore" or "license" (the project already has them).
5. Click **Create repository**. Keep the page open; it shows your repository address.

## 2. Upload the project
Open **Git Bash** (or PowerShell) and run these lines one by one.
Replace `YOUR-NAME` with your GitHub user name.

```
cd "C:/Users/rakes/Downloads/rag dataset/agent"
git init
git config core.autocrlf true
git add .
git commit -m "Voron 0.2 diagnostic assistant: final model, interface and evaluation"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/voron-diagnostic-assistant.git
git push -u origin main
```

If git asks who you are (first commit only), run these two lines with your own name and email, then repeat `git commit ...`:
```
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

When you push the first time, a browser window opens to sign in to GitHub. Upload is about 75 MB, so it can take a few minutes.

## 3. Check
Refresh the GitHub page. You should see about 254 files and the README.

## Later changes
```
git add .
git commit -m "short description of the change"
git push
```

## What is not uploaded (see .gitignore)
The 32 MB original STEP download, the assistant's session logs, Python cache files and two local helper files.
