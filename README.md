# 3. Automatikus kódoptimalizálás

**Feladat azonosítója és címe:** 3. Automatikus kódoptimalizálás  
**Beadó:** Bence Gyurus  
**Git repository:** [https://github.com/BenceGyurus/code-optimizer](https://github.com/BenceGyurus/code-optimizer)

Ez a projekt egy mérésvezérelt, LLM-alapú kódoptimalizáló keretrendszer. A célja nem az, hogy egy modell egyszerűen “írjon egy gyorsabb verziót”, hanem az, hogy a modell kontrollált eszközökön keresztül dolgozzon: először mérjen baseline-t, profilozza a kódot, válasszon konkrét célfüggvényt, javasoljon patch-et, majd a rendszer tesztekkel és újraméréssel döntse el, hogy a változtatás valóban jobb lett-e. A program így nem vakon fogadja el az AI válaszát, hanem csak akkor tekinti sikeresnek az optimalizációt, ha a kód továbbra is helyes és mérhetően gyorsabb.

A megoldás kétféle futtatási módot támogat. Az `optimizer run` egyetlen optimalizálási sessiont futtat le, az `optimizer evaluate` pedig modellekből, prompt pack-ekből és ismétlésekből álló kísérleti mátrixot kezel. Az evaluator minden futásról külön session könyvtárat, aggregált CSV/YAML eredményeket, Markdown riportot és diagramokat készít. A mérésekben a benchmark és a hardveres profilozás több ismétlés átlagából készül, ezért a runtime eredmények nem egyetlen véletlen futásra épülnek.

## A rendszer fő eszközei

| Tool | Szerep |
| --- | --- |
| `inspect_codebase` | Kontextust ad a modellnek a projektről, fájlokról és releváns kódrészletekről. |
| `run_baseline` | Lefuttatja az alap teszteket, benchmarkot és hardveres méréseket. |
| `profile_execution` | cProfile és `perf` alapján megmutatja a forró pontokat. |
| `analyze_candidate` | A modell kiválasztja, melyik függvényt vagy fájlt érdemes optimalizálni. |
| `propose_change` | A modell strukturált patch-et javasol. |
| `apply_and_verify` | A rendszer alkalmazza a patch-et, majd tesztekkel ellenőrzi. |
| `remeasure` | Újraméri az optimalizált kód futási idejét és hardveres mutatóit. |
| `evaluate_result` | Eldönti, hogy az eredmény elfogadható-e, vagy kell további próbálkozás. |
| `rollback_to_checkpoint` | Hibás vagy lassító módosítás esetén visszaállítja a biztonságos állapotot. |

A projektben több promptolási stratégia is található a `prompts/` mappában. A legfontosabbak: `zero_shot`, `few_shot`, `knowledge_gen`, `hardware_focus`, `hypothesis_driven`, `self_refine`, `agentic`, `cot`, `least_to_most` és `prompt_chaining`. Ezek ugyanazt az optimalizáló állapotgépet használják, de más gondolkodási mintát adnak a modellnek. Például a `hardware_focus` a cache- és branch-miss jellegű metrikákra érzékenyebb, a `self_refine` nagyobb hangsúlyt ad a saját javaslat ellenőrzésére, a `few_shot` példákból vezeti le a kívánt viselkedést, a `knowledge_gen` előbb háttértudást és hipotézist épít, míg a `hypothesis_driven` minden döntést egy mérhető feltételezéshez köt.

## Kiemelt prompt pack: `hypothesis_driven`

A mérések alapján a legjobban védhető prompt pack a `hypothesis_driven`, ezért ezt választottam ki részletesebben. A heavy benchmark OpenRouter futásain ez adta az egyik legjobb átlagos gyorsulást, a többfájlos complex pipeline tesztben pedig már eleve ezzel futottak a legerősebb modellek. A stratégia lényege, hogy a modell ne általános optimalizációs ötleteket dobáljon, hanem minden lépés előtt fogalmazzon meg egy konkrét hipotézist: melyik metrikának kell javulnia, miért pont az adott kódrészlet a szűk keresztmetszet, és hogyan fogja ezt a patch befolyásolni.

| Prompt fájl | Mire való |
| --- | --- |
| `master.md` | Meghatározza a modell szerepét, a runtime szerződést, az állapotot, a megengedett actionöket és a méréshez kötött gondolkodást. |
| `decision.md` | Minden lépésnél kiválasztja a következő toolt az állapotgépben, kizárólag érvényes JSON válasszal. |
| `analyze_candidate.md` | Egy konkrét hotspot kiválasztását kéri, mérési hipotézissel és várható jellel együtt. |
| `propose_change.md` | Strukturált patch-et kér a jelenlegi célpontra, rövid indoklással és várható mérhető hatással. |
| `evaluate_result.md` | Összeveti az elvárt és megfigyelt eredményt, majd eldönti, hogy meg kell-e állni vagy folytatni kell. |
| `config.yaml` | A prompt pack neve, verziója és rövid leírása. |

## Eredmények és alátámasztás

A végső mérésekben kétféle benchmark szerepelt. Az `examples/heavy_compute.py` egy single-file, erősen algoritmikus optimalizálási feladat volt, ahol a nagy OpenRouter modellek stabilan megtalálták a domináns `segmented_prefix_sums_slow` hotspotot, és az O(n²) jellegű prefix-számítást O(n) futó összeges megoldásra cserélték. A többfájlos `examples/complex_pipeline` ennél nehezebb volt, mert több fájl, több wrapper függvény és több kisebb hotspot között kellett választani. Itt jobban kijött, hogy nem elég a nagy kumulatív futásidőt nézni: a jó megoldás a tényleges self-time hotspotot célozta, például a `customer_recent_totals` függvényt.

![Modellek gyorsulása benchmarkonként](docs/experiments/debian-combined-llm-prompt-analysis/charts/speedup_by_dataset_model.png)

![Prompt pack-ek összehasonlítása a heavy benchmarkon](docs/experiments/debian-combined-llm-prompt-analysis/charts/heavy_prompt_speedup_heatmap.png)

![Patch próbálkozások kimenetele modellenként](docs/experiments/debian-combined-llm-prompt-analysis/charts/patch_status_by_model.png)

A legfontosabb tapasztalat az volt, hogy a nagyobb modellek nem feltétlenül “kreatívabb” megoldást találtak, hanem stabilabban vitték végig ugyanazt a jó mérnöki döntést. A Gemini 3.1 Pro, a GPT-OSS 120B és a GPT-5.3 Codex a heavy benchmarkon 7-8x körüli gyorsulást értek el. A self-hostolt Qwen 2.5 Coder 7B ezzel szemben sokszor közel járt a jó célponthoz, de a patch formátuma vagy a szemantikai helyessége nem volt elég stabil, ezért a rendszer nem fogadta el az optimalizációkat. Ez nem hiba volt, hanem hasznos eredmény: jól látszott, hogy az olcsóbb vagy lokális modell nem biztos, hogy a teljes optimalizálási ciklusban is olcsóbb, ha sok sikertelen próbálkozást termel.

A fejlesztés közben több gyakorlati probléma is előjött. Javítani kellett a promptokat, hogy a modell ne ismételjen végtelen inspect-loopot, ne adjon hibás JSON-t, és értse, hogy milyen toolok és állapotok léteznek. Külön kezelni kellett a Linuxos `perf` működését, a cache-hit metrikák értelmezését, az unsupported LLC countereket, valamint azt is, hogy a többfájlos projektek ne egyetlen óriási kontextusként kerüljenek a modell elé. A végeredményben a rendszer már package directoryt is tud másolni, több fájlból kompakt AST-vázlatot és célzott kódrészleteket ad a modellnek, majd a patch-et a megfelelő workspace-ben alkalmazza.

## Futtatás

Fejlesztés közben a CLI telepítés nélkül is futtatható:

```bash
PYTHONPATH=src .venv/bin/python -m optimizer.cli doctor
```

Egy olcsó smoke teszt Debianon:

```bash
OPENROUTER_API_KEY=sk-or-... ./scripts/evaluate_debian_smoke.sh examples/complex_pipeline results/debian-smoke-complex
```

A komplex, többfájlos végső futás:

```bash
OPENROUTER_API_KEY=sk-or-... RUN_REPETITIONS=15 ./scripts/evaluate_debian_complex.sh
```

## Tanulság

A feladat legfontosabb tanulsága, hogy az AI-alapú kódoptimalizálás akkor működik jól, ha nem önmagában egy promptból áll, hanem mérés, tesztelés, visszacsatolás és rollback is köré van építve. Egy modell tud javasolni jó ötletet, de a programnak kell eldöntenie, hogy az ötlet tényleg helyes és gyorsabb-e. Emiatt a projekt számomra nem csak arról szólt, hogy melyik modell mennyit gyorsít, hanem arról is, hogy hogyan lehet az AI-t egy mérnöki folyamat részévé tenni: mérhető hipotézissel, ellenőrzött patch-csel, automatikus újraméréssel és dokumentálható eredményekkel.

Részletesebb elemzés és további diagramok: [docs/experiments/debian-combined-llm-prompt-analysis/README.md](docs/experiments/debian-combined-llm-prompt-analysis/README.md)

Technikai használati útmutató a CLI-hez és a régi architekturális leíráshoz: [USERMANUAL.md](USERMANUAL.md)

## Ellenőrzés

```bash
PYTHONPATH=src .venv/bin/python -m compileall -q src/optimizer
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m optimizer.cli doctor
```
