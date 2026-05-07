# User Manual

Ez a dokumentum a projekt technikai használati útmutatója. A gyökér [README.md](README.md) inkább a beadandó rövidebb, értelmező leírása, ez a fájl pedig azt írja le részletesebben, hogyan lehet a programot telepíteni, futtatni, konfigurálni és az eredményeket értelmezni.

## Rövid áttekintés

A program egy LLM-alapú, mérésvezérelt kódoptimalizáló keretrendszer. A célja az, hogy egy AI modellt ne közvetlenül, kontroll nélkül engedjen rá a kódra, hanem egy állapotgéppel, toolokkal, tesztekkel és benchmarkokkal körbevett folyamatban használjon.

Két fő futtatási mód van:

- `optimizer run`: egyetlen optimalizálási sessiont indít egy projektre.
- `optimizer evaluate`: több modell, prompt pack és ismétlés alapján teljes kísérleti mátrixot futtat.

A program nem az eredeti projektfájlokat módosítja közvetlenül. Minden futáshoz külön workspace készül a `results/` alatt, és a patch-ek ott futnak le. Ha egy patch hibás, elbuknak a tesztek, vagy nem lesz gyorsabb a kód, a session rollbackelhető, illetve sikertelenként kerül az eredmények közé.

## Telepítés

Python 3.10 vagy újabb kell hozzá. Fejlesztés közben telepítés nélkül is futtatható a `PYTHONPATH=src` használatával.

```bash
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[dev]"
```

Ha csak a minimális futtatás kell:

```bash
.venv/bin/pip install -e .
```

Debianon a hardveres metrikákhoz `perf` is kell:

```bash
sudo apt update
sudo apt install linux-perf
```

Ha a `perf` hozzáférés tiltva van, akkor tipikusan ezt kell beállítani:

```bash
sudo sysctl kernel.perf_event_paranoid=1
```

Tartós beállításhoz:

```bash
echo 'kernel.perf_event_paranoid=1' | sudo tee /etc/sysctl.d/99-perf.conf
sudo sysctl --system
```

Fontos, hogy bizonyos counterek, például `LLC-loads` és `LLC-load-misses`, hardvertől, kerneltől vagy virtualizációtól függően nem mindig támogatottak. A Debian helper scriptek ezt ellenőrzik, és a nem támogatott countereket kihagyják.

## Alapellenőrzés

Telepítés után érdemes ezt futtatni:

```bash
PYTHONPATH=src .venv/bin/python -m optimizer.cli doctor
```

Ez kiírja:

- milyen toolok vannak regisztrálva,
- mely providerek érhetők el,
- mely prompt pack-ek vannak meg és hiánytalanok-e.

A kód gyors ellenőrzésére:

```bash
PYTHONPATH=src .venv/bin/python -m compileall -q src/optimizer
PYTHONPATH=src .venv/bin/python -m pytest -q
```

## Projektstruktúra

```text
src/optimizer/
  cli.py                       # Typer CLI belépési pont
  orchestrator/                # session állapotgép, guardrailek, fő futtatási logika
  tools/                       # inspect, baseline, profile, patch, verify, remeasure toolok
  providers/                   # OpenRouter, Ollama, OpenAI, Gemini, Anthropic, CLI providerek
  llm/                         # prompt betöltés, prompt építés, JSON válasz parsing, source context
  evaluation/                  # evaluate mód, aggregálás, riportok, diagramok
  execution/                   # shell parancsok futtatása
  artifacts/                   # session artifactok mentése
  state/                       # checkpointok és session állapot

prompts/                       # prompt pack-ek
examples/                      # optimalizálható példaprogramok
scripts/                       # Debian futtató scriptek
docs/experiments/              # commitolt elemzések és diagramok
results/                       # lokális futási eredmények, gitignore-olva
```

## Állapotgép

A sessionöket egy explicit állapotgép vezérli. Ez akadályozza meg, hogy a modell bármilyen sorrendben hívjon toolokat vagy végtelen ciklusban ragadjon.

```text
INIT
BASELINE_READY
PROFILE_READY
ANALYSIS_READY
PATCH_PROPOSED
PATCH_APPLIED
VERIFIED
REMEASURED
DONE
FAILED
```

A lényegi folyamat:

1. `INIT`: indulás, itt baseline mérés vagy kódbázis-áttekintés kérhető.
2. `BASELINE_READY`: már van alap futási idő és teszteredmény.
3. `PROFILE_READY`: rendelkezésre állnak profilozási adatok.
4. `ANALYSIS_READY`: a modell kiválasztott egy optimalizálási célpontot.
5. `PATCH_PROPOSED`: van javasolt patch, de még nincs elfogadva.
6. `PATCH_APPLIED`: a patch bekerült a workspace-be.
7. `VERIFIED`: a módosított kód átment a teszteken.
8. `REMEASURED`: a módosított kód újra lett mérve.
9. `DONE`: a session sikeresen vagy kontrolláltan lezárult.
10. `FAILED`: a session hibával vagy sikertelen optimalizációval zárult.

A guardrailek három fő limitet használnak:

- `--max-llm-calls`: maximum LLM hívások száma.
- `--max-tool-calls`: maximum tool hívások száma.
- `--max-iterations`: maximum optimalizációs iterációk száma.

Ha a modell hibás JSON-t ad, túl sokszor ismétel egy lépést, elfogy a budget, vagy a patch nem működik, a session nem fut tovább végtelenül.

## Toolok

| Tool | Szerep |
| --- | --- |
| `inspect_codebase` | Áttekintést ad a projektről, fájlokról és releváns kódrészletekről. |
| `run_baseline` | Lefuttatja a tesztet, benchmarkot, hardveres profilt és opcionális function profile-t. |
| `profile_execution` | Külön profilozási lépés, ha a modell részletesebb mérést kér. |
| `analyze_candidate` | A modell kiválasztja, melyik célpontot optimalizálná. |
| `propose_change` | A modell patch-et javasol. |
| `apply_and_verify` | Alkalmazza a patch-et, majd build/test verifikációt futtat. |
| `remeasure` | Újraméri az optimalizált kódot. |
| `evaluate_result` | Összehasonlítja a baseline és optimized eredményeket. |
| `rollback_to_checkpoint` | Visszaállítja a korábbi biztonságos állapotot. |

## Prompt pack-ek

Minden prompt pack a `prompts/<pack-name>/` mappában található, és ezekből a fájlokból áll:

```text
master.md
decision.md
analyze_candidate.md
propose_change.md
evaluate_result.md
config.yaml
```

A fájlok szerepe:

- `master.md`: általános rendszerleírás, állapotgép, tool szerződés, output szabályok.
- `decision.md`: a következő action kiválasztása.
- `analyze_candidate.md`: célpont kiválasztása és stratégia megfogalmazása.
- `propose_change.md`: patch generálása.
- `evaluate_result.md`: baseline és optimized eredmények összevetése.
- `config.yaml`: név, verzió és leírás.

Elérhető prompt pack-ek:

- `agentic`
- `concise`
- `cot`
- `default`
- `few_shot`
- `hardware_focus`
- `hypothesis_driven`
- `knowledge_gen`
- `least_to_most`
- `negative_constraints`
- `one_shot`
- `prompt_chaining`
- `reasoning_goal`
- `role_create`
- `self_refine`
- `structured_tags`
- `zero_shot`

A végső méréseknél a `hypothesis_driven` bizonyult a legjobban védhető stratégiának, mert minden optimalizálási lépést mérhető hipotézishez köt. A heavy benchmarkon több prompt pack futott, a komplex többfájlos mérésnél már főleg a legjobban működő prompt pack és modellek szerepeltek.

## Provider konfiguráció

A providerek a `src/optimizer/providers/` alatt vannak. A regisztrált providerek:

- `mock`
- `openai`
- `gemini`
- `anthropic`
- `openrouter`
- `openai-codex-cli`
- `ollama`
- `gemini-cli`
- `github-copilot-cli`

### OpenRouter

OpenRouter használatához:

```bash
export OPENROUTER_API_KEY=sk-or-...
```

Hasznos környezeti változók:

```bash
export OPENROUTER_RESPONSE_FORMAT=off
export OPENROUTER_TIMEOUT=180
export OPENROUTER_SITE_URL=http://localhost
export OPENROUTER_APP_NAME=optimizer-framework
```

Az `OPENROUTER_RESPONSE_FORMAT=off` azért volt hasznos, mert egyes OpenRouter modellek, főleg free modellek, nem szeretik a kötelező JSON response format módot. A prompt ettől még JSON választ kér.

### Ollama

Ollama helyi vagy hálózati szerverrel használható:

```bash
export OLLAMA_HOST=http://192.168.1.46:11434
export OLLAMA_MODEL_ID=qwen2.5-coder:7b
export OLLAMA_FORMAT=json
export OLLAMA_THINK=false
export OLLAMA_ENDPOINT=chat
export OLLAMA_TIMEOUT=900
```

A futás előtt érdemes ellenőrizni, hogy a modell elérhető:

```bash
curl http://192.168.1.46:11434/api/tags
```

A projektben használt self-hostolt Qwen modell egy NVIDIA P104-100 8 GB VRAM-os videókártyán futott. Ilyenkor különösen fontos a rövid JSON válasz és a tömörített mérési kontextus, mert a kisebb lokális modellek könnyebben elvesznek nagy promptokban.

## CLI használat

Telepítés nélkül:

```bash
PYTHONPATH=src .venv/bin/python -m optimizer.cli doctor
```

Telepített csomagként:

```bash
optimizer doctor
```

### Egyetlen session futtatása

```bash
REPO_ROOT="$(pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

PYTHONPATH="${REPO_ROOT}/src" "${PYTHON_BIN}" -m optimizer.cli run \
  --project examples/heavy_compute.py \
  --provider openrouter \
  --model openai/gpt-oss-120b \
  --prompt-pack hypothesis_driven \
  --test-command "\"${PYTHON_BIN}\" \"${REPO_ROOT}/scripts/repeat_unittest_summary.py\" --pattern heavy_compute.py --repetitions 15" \
  --benchmark-command "\"${PYTHON_BIN}\" heavy_compute.py --skip-tests --repetitions 1" \
  --profile-command "perf stat -e cache-references,cache-misses,branches,branch-misses -- \"${PYTHON_BIN}\" heavy_compute.py --skip-tests --repetitions 1" \
  --runtime-repetitions 15 \
  --hardware-repetitions 15 \
  --max-llm-calls 16 \
  --max-tool-calls 32 \
  --max-iterations 4 \
  --output-dir results/manual-run-heavy
```

Ez egyetlen modellt és prompt pack-et próbál ki.

### Kísérleti mátrix futtatása

```bash
REPO_ROOT="$(pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

PYTHONPATH="${REPO_ROOT}/src" "${PYTHON_BIN}" -m optimizer.cli evaluate \
  --project examples/heavy_compute.py \
  --provider-models "openrouter=openai/gpt-oss-120b,openrouter=google/gemini-3.1-pro-preview" \
  --prompt-packs "zero_shot,hypothesis_driven,few_shot" \
  --repetitions 1 \
  --runtime-repetitions 15 \
  --hardware-repetitions 15 \
  --test-command "\"${PYTHON_BIN}\" \"${REPO_ROOT}/scripts/repeat_unittest_summary.py\" --pattern heavy_compute.py --repetitions 15" \
  --benchmark-command "\"${PYTHON_BIN}\" heavy_compute.py --skip-tests --repetitions 1" \
  --profile-command "perf stat -e cache-references,cache-misses,branches,branch-misses -- \"${PYTHON_BIN}\" heavy_compute.py --skip-tests --repetitions 1" \
  --output-dir results/manual-eval-heavy \
  --max-llm-calls 16 \
  --max-tool-calls 32 \
  --max-iterations 4 \
  --no-deterministic-fallback \
  --verbose
```

Az `--provider-models` formátuma:

```text
provider=model,provider=model
```

Például:

```text
openrouter=openai/gpt-oss-120b,ollama=qwen2.5-coder:7b
```

## Fontos CLI opciók

| Opció | Jelentés |
| --- | --- |
| `--project` | Optimalizálandó fájl vagy projektmappa. |
| `--provider` | Egy provider neve `run` módban. |
| `--model` | Egy modell neve `run` módban. |
| `--provider-models` | Provider-modell párok `evaluate` módban. |
| `--prompt-pack` / `--prompt-packs` | Egy vagy több prompt stratégia. |
| `--build-command` | Opcionális build parancs. |
| `--test-command` | Tesztparancs. |
| `--benchmark-command` | Runtime méréshez használt parancs. |
| `--profile-command` | Hardveres profilozási parancs, például `perf stat`. |
| `--function-profile-command` | Függvényszintű profilozás, például `cProfile`. |
| `--repetitions` | Hány session fusson konfigurációnként. |
| `--runtime-repetitions` | Hányszor fusson a benchmark baseline és remeasure esetén. |
| `--hardware-repetitions` | Hányszor fusson a hardveres profilozás. |
| `--function-profile-repetitions` | Hányszor fusson a function profiler. |
| `--max-llm-calls` | LLM hívások felső korlátja. |
| `--max-tool-calls` | Tool hívások felső korlátja. |
| `--max-iterations` | Optimalizálási iterációk felső korlátja. |
| `--allow-deterministic-fallback` | Engedélyezi a deterministic fallback patcheket, ha van ilyen. |
| `--no-deterministic-fallback` | Tiltja a fallbacket, a méréseknél ezt használtuk. |
| `--output-dir` | Eredmények célmappája. |
| `--verbose` / `--quiet` | Részletes konzolos logolás kapcsolása. |

## Debian helper scriptek

A kézi CLI parancsok hosszúak, ezért a mérésekhez helper scriptek készültek.

### Smoke teszt

```bash
OPENROUTER_API_KEY=sk-or-... \
RUN_REPETITIONS=15 \
./scripts/evaluate_debian_smoke.sh examples/heavy_compute.py results/debian-smoke-heavy
```

Jellemző alapértékek:

- provider/model: `openrouter=openai/gpt-oss-120b:free`
- prompt pack: `knowledge_gen`
- runtime/hardware repetitions: `RUN_REPETITIONS`, alapból 15
- max LLM calls: 14
- max tool calls: 28
- max iterations: 3

Directory projektre is használható:

```bash
OPENROUTER_API_KEY=sk-or-... \
PROJECT_MODULE=market_sim \
./scripts/evaluate_debian_smoke.sh examples/complex_pipeline results/debian-smoke-complex
```

### Heavy full mérés

```bash
OPENROUTER_API_KEY=sk-or-... \
RUN_REPETITIONS=15 \
./scripts/evaluate_debian_full.sh examples/heavy_compute.py results/debian-full-heavy
```

Alap modellek:

```text
openrouter=openai/gpt-oss-120b
openrouter=google/gemini-3.1-pro-preview
openrouter=openai/gpt-5.3-codex
ollama=qwen2.5-coder:7b
```

Alap prompt pack-ek:

```text
zero_shot,knowledge_gen,hardware_focus,hypothesis_driven,self_refine,few_shot
```

Szűkített pilot futáshoz:

```bash
PROVIDER_MODELS="openrouter=openai/gpt-oss-120b" \
PROMPT_PACKS="hypothesis_driven" \
RUN_REPETITIONS=5 \
OPENROUTER_API_KEY=sk-or-... \
./scripts/evaluate_debian_full.sh examples/heavy_compute.py results/pilot-heavy
```

### Complex pipeline mérés

```bash
OPENROUTER_API_KEY=sk-or-... \
RUN_REPETITIONS=15 \
./scripts/evaluate_debian_complex.sh
```

Alap projekt:

```text
examples/complex_pipeline
```

Alap modellek:

```text
openrouter=google/gemini-3.1-pro-preview
openrouter=openai/gpt-oss-120b
openrouter=openai/gpt-5.3-codex
```

Alap prompt pack:

```text
hypothesis_driven
```

Más output mappával:

```bash
OPENROUTER_API_KEY=sk-or-... \
./scripts/evaluate_debian_complex.sh examples/complex_pipeline results/my-complex-run
```

## Példaprojektek

### `examples/heavy_compute.py`

Egy egyfájlos, erősen számításigényes példa. Saját unittest teszteket tartalmaz, és CLI-ként is futtatható.

Teszt:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s examples -p "heavy_compute.py" -q
```

Benchmark:

```bash
cd examples
../.venv/bin/python heavy_compute.py --skip-tests --repetitions 1
```

### `examples/complex_pipeline`

Többfájlos Python package, amely a `market_sim` modult tartalmazza. Ez jobban modellezi azt, amikor az optimalizálás nem egyetlen fájlban történik.

Teszt:

```bash
cd examples/complex_pipeline
../../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q
```

Benchmark:

```bash
cd examples/complex_pipeline
../../.venv/bin/python -m market_sim --skip-tests --repetitions 1
```

Function profile:

```bash
cd examples/complex_pipeline
../../.venv/bin/python -m cProfile -s cumulative -m market_sim --skip-tests --repetitions 1
```

## Eredmények felépítése

Egy `optimizer run` session tipikusan így néz ki:

```text
results/session_<timestamp>/
  workspace/
  checkpoint/
  final_summary.yaml
  tool_output_*.json
  transcript.jsonl
```

Egy `optimizer evaluate` futás:

```text
results/eval_<timestamp>_<id>/
  experiment_matrix.yaml
  aggregated_results.csv
  aggregated_results.yaml
  report.md
  charts/
  per_run/
```

Fontosabb fájlok:

- `experiment_matrix.yaml`: mely provider/model/prompt/repetition kombinációk futottak.
- `aggregated_results.csv`: táblázatos eredmények minden sessionről.
- `aggregated_results.yaml`: aggregált, géppel jól olvasható eredmények.
- `report.md`: embernek olvasható összefoglaló.
- `charts/`: generált diagramok.
- `per_run/`: sessionönkénti részletes artifactok.

## Diagramok és metrikák

A program többféle chartot tud készíteni, ha van elég adat:

- baseline vs optimized runtime,
- relative speedup,
- success/failure arány,
- tool usage,
- LLM calls per run,
- tool calls per run,
- iterations per run,
- cache hit/miss before-after,
- L1 cache hit/miss before-after,
- LLC hit/miss before-after, ha a gép támogatja,
- branch miss before-after.

Az LLC chartoknál előfordulhat `n/a`, ha a gép vagy VM nem támogatja az adott perf countereket. Ez nem feltétlen programhiba.

## Eredmények értelmezése

A legfontosabb elsődleges metrika a runtime és a speedup. A hardveres metrikák segítenek megérteni, mi történt, de nem mindig önmagukban döntőek.

Például:

- Ha a runtime sokat javul, de a cache hit-rate romlik, attól még lehet jó az optimalizáció.
- Ha egy patch teszteken elbukik, akkor nem elfogadható, akkor sem, ha elméletben gyorsabb lenne.
- Ha a modell sok toolt vagy LLM hívást használ, de nincs jobb eredmény, akkor az adott modell/prompt drágább vagy bizonytalanabb.
- Ha minden nagy modell hasonló speedupot ér el, akkor valószínűleg a benchmarkban egy domináns, könnyen megtalálható algoritmikus hotspot van.

## Tipikus hibák és megoldások

### `perf hardware counters are not available`

Ok: a kernel tiltja a perf countereket, vagy VM-ben nincs hozzáférés.

Megoldás:

```bash
sudo sysctl kernel.perf_event_paranoid=1
```

Ha így sem működik, lehet, hogy a VM/hardver nem adja tovább a countereket.

### LLC metrikák `n/a`

Ok: `LLC-loads` vagy `LLC-load-misses` nem támogatott az adott gépen.

Megoldás: ha fizikai gépen fut, BIOS/kernel beállítás segíthet, de sok esetben nem javítható szoftverből. A Debian scriptek automatikusan kihagyják a nem támogatott countereket.

### OpenRouter JSON hibák

Ok: egyes modellek nem támogatják jól a `response_format=json_object` módot.

Megoldás:

```bash
export OPENROUTER_RESPONSE_FORMAT=off
```

### Ollama nem elérhető

Ellenőrzés:

```bash
curl http://192.168.1.46:11434/api/tags
```

Ha nincs válasz, ellenőrizni kell az Ollama szervert, tűzfalat, IP címet és hogy a modell le van-e töltve.

### Túl sok token a modellnek

Megoldás:

- használj `repeat_unittest_summary.py`-t nyers ismételt tesztlogok helyett,
- többfájlos projektnél hagyd a source context buildert célzott kontextust adni,
- kisebb modelleknél szűkítsd a prompt pack-et és a max hívásokat.

### Végtelennek tűnő futás

A sessiont a guardrailek megállítják, de drága modelleknél érdemes alacsonyabb limitekkel pilotot futtatni:

```bash
--max-llm-calls 8 --max-tool-calls 16 --max-iterations 2
```

## Ajánlott munkamenet drága futás előtt

1. Futtasd a `doctor` parancsot.
2. Futtass smoke tesztet olcsó/free modellel.
3. Nézd meg, hogy készülnek-e chartok és átmennek-e a tesztek.
4. Futtass kis pilotot 1 modell + 1 prompt pack + 5 ismétléssel.
5. Csak ezután indíts teljes mátrixot 15 ismétléssel.

Példa pilot:

```bash
OPENROUTER_API_KEY=sk-or-... \
PROVIDER_MODELS="openrouter=openai/gpt-oss-120b:free" \
PROMPT_PACKS="hypothesis_driven" \
RUN_REPETITIONS=5 \
./scripts/evaluate_debian_smoke.sh examples/heavy_compute.py results/pilot-heavy
```

## Dokumentációs eredmények

A részletesebb commitolt elemzések itt vannak:

- [docs/experiments/debian-combined-llm-prompt-analysis](docs/experiments/debian-combined-llm-prompt-analysis)
- [docs/experiments/debian-full-heavy-1778099536167691431](docs/experiments/debian-full-heavy-1778099536167691431)

A lokális, teljes futási eredmények a `results/` mappában vannak, de ez gitignore-olva van, mert nagy és gépfüggő artifactokat tartalmaz.
