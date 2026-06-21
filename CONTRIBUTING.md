# Contributing to Quran Reels Generator

First off, thank you for considering contributing to the Quran Reels Generator! It's people like you that make the open-source community such a great place to learn, inspire, and create.

## 🤝 How Can I Contribute?

### 1. Reporting Bugs
If you find a bug, please use the **Bug Report** issue template. Before opening an issue, check if it has already been reported. Include as much detail as possible: your operating system, the environment you are running it in (Local vs Hugging Face), and error logs.

### 2. Suggesting Enhancements
Have an idea for a new feature? We'd love to hear it! Use the **Feature Request** issue template. If you can, explain *why* the enhancement would be useful to most users.

### 3. Pull Requests
1. Fork the repository and create your branch from `main`.
2. If you've added code that should be tested, ensure everything works correctly.
3. If you've changed the desktop UI or pipeline, run the build script `.\desktop\build_windows.ps1 -SkipInstaller` locally to verify you haven't broken the PyInstaller build.
4. Update the `README.md` with details of changes if applicable.
5. Issue that pull request!

## 💻 Development Setup

### Local Backend/Frontend Dev
1. Clone the repo: `git clone https://github.com/Afrasyaab-GH/Quran-Reels-Generator.git`
2. Run the `run-local.ps1` script (on Windows) or manually set up a `venv` and `pip install -r requirements.txt`.
3. The main logic lives in `main.py` (API and routing) and `video.py` (the actual rendering pipeline).
4. The frontend lives entirely in `UI.html`. You can make edits to the HTML/JS/CSS and simply refresh the page!

### Translation and Localization (i18n)
If you wish to add a new UI language or a new translation for the Quranic text, check out `i18n.py` and `audio.py`.

## 📜 Code of Conduct
By participating in this project, you agree to maintain a respectful and welcoming environment for everyone. Since this is an Islamic-oriented project, we ask all contributors to adhere to high standards of manners, respect, and constructive communication.

Jazakallah Khair for your contributions!
