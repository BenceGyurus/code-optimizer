# 🚀 OptiCode: Enterprise & CI/CD Edition

Az **OptiCode** egy intelligens, hibrid kódoptimalizáló, amely egyesíti a statikus analízist és az LLM erejét.

## 🛠️ Főbb Funkciók
- **Hibrid Elemzés:** AST Hunter + Ruff Linter.
- **CI Pipeline Mód (`--ci`):** Teljesen automatizált, teszt-vezérelt optimalizálás emberi beavatkozás nélkül.
- **Git Workflow Integráció:** Automatikus ágkezelés és commit minden változtatás után.
- **Intelligens Caching:** Helyi gyorstárazás a költségek csökkentésére.
- **Automatikus Verifikáció & Rollback:** Azonnali visszaállítás hibás optimalizálás esetén.
- **PEP8 Import Normalization:** Automatikus import rendezés a fájlok tetejére.

---

## 🏗️ Hogyan működik? (Architektúra)

```mermaid
graph TD
    A[Python fájlok / mappák] --> B{Szkennelés fázis}
    
    subgraph "Statikus Analízis"
        B --> B1[AST Hunter: Ciklusok, Redundancia]
        B --> B2[Ruff Linter: Hibák, Bad Practices]
    end
    
    B1 --> C[Találatok gyűjtése]
    B2 --> C
    
    C --> D[Few-shot Prompt építés]
    D --> E[LLM Gateway: Gemini / Ollama]
    
    E --> F[Optimalizált kódblokk + Metaadatok]
    
    F --> G[TUI: Diff megjelenítés & Indoklás]
    G --> H{Felhasználói döntés?}
    
    H -- Igen --> I[Patcher: Fájl módosítása]
    I --> J{Van tesztparancs?}
    
    J -- Van --> J1[Tesztfuttatás]
    J1 -- Elbukott --> J2[Rollback: Visszaállítás]
    J1 -- Sikerült --> K
    
    J -- Nincs --> K{Változott a fájl?}
    K -- Igen --> B
    K -- Nem --> L[Következő fájl / Vége]
```

---

## 🚀 Használat

### Pipeline-ban (CI/CD):
A `--ci` módhoz kötelező megadni egy tesztparancsot. Ha a tesztek elbuknak, az OptiCode automatikusan visszavonja a hibás változtatást.
```bash
python cli.py . --ci --test-cmd "pytest"
```

### Interaktív módban:
Végigvezet a változtatásokon, diffet mutat és jóváhagyást kér.
```bash
python cli.py main.py --test-cmd "python tests.py"
```

### Paraméterek:
- `path`: Mappa vagy fájl elérési útja.
- `--ci`: Pipeline mód (nincs diff, nincs prompt, kötelező a `--test-cmd`).
- `--test-cmd`: A verifikációhoz használt parancs.
- `--git-branch`: Új git ág és commitok minden módosításhoz.
- `--allow-edit` / `-y`: Automatikus javítás (interaktív módban is).

---

## ⚙️ Telepítés
```bash
pip install -r requirements.txt
pip install ruff
```

---

## 📊 Statisztikák
A futtatás végén az OptiCode egy összefoglaló táblázatot mutat a felhasznált tokenekről és a becsült költségről.
