# 3. Automatikus kódoptimalizálás

**Feladat azonosítója és címe:** 3. Automatikus kódoptimalizálás  
**Beadó:** Bence Gyurus  
**Git repository:** [https://github.com/BenceGyurus/code-optimizer](https://github.com/BenceGyurus/code-optimizer)

Ennél a feladatnál azt szerettem volna kipróbálni, hogy mennyire lehet LLM-eket nem csak egyszerű kódgenerálásra használni, hanem egy kontrolláltabb optimalizálási folyamat részeként. A lényeg az volt, hogy a modell ne csak ránézésre írjon át valamit, hanem előtte mérjen, nézze meg a kódot, válasszon egy konkrét célpontot, készítsen patch-et, majd a program tesztekkel és újraméréssel ellenőrizze, hogy tényleg jobb lett-e. Így a modell nem önállóan dönt arról, hogy sikerült-e az optimalizálás, hanem a program csak akkor fogadja el a változtatást, ha a kód továbbra is helyes és mérhetően gyorsabb.

A programot a saját instrukcióim és folyamatos döntéseim alapján készítettem, de a megvalósítás nagy részében Codex-et használtam fejlesztőtársként. Tehát nem csak egy kész promptot futtattam le, hanem közben végig irányítottam, hogy milyen működés kell, milyen hibákat kell javítani, milyen teszteket akarok futtatni, és milyen eredmények legyenek elfogadhatóak. A Codex főleg a kódolásban, refaktorálásban, promptok átírásában, shell scriptek elkészítésében és a dokumentáció összerakásában segített. 

A megoldás közben két fő futtatási mód készült. Az `optimizer run` egyetlen optimalizálási sessiont futtat, az `optimizer evaluate` pedig több modellből, prompt pack-ből és ismétlésből álló mérést tud elvégezni. Nekem a második volt a fontosabb, mert így össze lehetett hasonlítani különböző modelleket és promptolási stratégiákat. A futások végén a program külön mappákba menti az egyes sessionöket, készít `CSV` és `YAML` eredményeket, Markdown riportot és diagramokat is. A benchmark és a hardveres mérés nem egyetlen futásból jön ki, hanem több ismétlés átlagából, például a végső méréseknél 15 futásból.

Fontos része volt a megoldásnak az is, hogy a modell ne tudjon végtelenségig futni. Ezt úgy oldottam meg, hogy a programban van egy állapotgép, és minden állapotban csak bizonyos toolokat lehet meghívni. Például baseline mérés előtt nem lehet patch-et alkalmazni, patch után pedig kötelező a verifikáció. Emellett minden session kap felső korlátot az LLM hívásokra, tool hívásokra és iterációkra (`--max-llm-calls`, `--max-tool-calls`, `--max-iterations`). Erre azért volt szükség, mert a korai futásoknál volt olyan modell, ami ugyanazt az inspect vagy propose lépést kérte újra és újra, illetve volt olyan is, amelyik hibás JSON-t adott vissza. Ilyenkor a guardrail megállítja a folyamatot, rollbackel, vagy `DONE`/`FAILED` állapotba viszi a sessiont.

## A program működése

A program lényege az, hogy az AI-t ne közvetlen kódátíróként használja, hanem egy mérésvezérelt optimalizálási folyamat döntéshozó részeként. Az alapelv az, hogy előbb mérni kell, csak utána szabad módosítani. Emiatt a modell nem abból indul ki, hogy "ránézésre ez lassú", hanem kap baseline futási időt, teszteredményt, profilozási adatokat, hardveres metrikákat és kódrészleteket. Ezek alapján kell eldöntenie, hogy hol érdemes beavatkozni. A cél nem az, hogy mindenáron átírjon minél több kódot, hanem hogy egy konkrét, mérhető szűk keresztmetszetet találjon, és arra adjon minél kisebb, ellenőrizhető javítást.

Az optimalizálásnál a program főleg néhány mérnöki elvet próbál követni. Először algoritmikus javítást keres, mert egy O(n²) megoldás O(n)-re cserélése sokkal többet érhet, mint apró lokális gyorsítások. Második szempont, hogy a változtatás legyen kicsi és célzott, tehát ne írja át feleslegesen az egész programot. Harmadik szempont, hogy a kód viselkedése ne változzon meg, ezért minden patch után teszt fut. Negyedik szempont, hogy a runtime legyen az elsődleges metrika, a cache, L1, branch és LLC adatok pedig inkább magyarázzák az eredményt, ne önmagukban döntsenek. Ez azért fontos, mert egy cache hit-rate romlás mellett is lehet sokkal gyorsabb a program, ha közben nagyságrendekkel kevesebb munkát végez.

A modellnek a program nem nyers, végtelen hosszú logokat ad be, hanem rövidített és strukturált adatokat. Ilyen például a tesztek összefoglalója, a benchmark átlag/minimum/maximum értékei, a profilozó által jelzett legfontosabb függvények, a hardveres metrikák átlaga, a jelenlegi állapot, az engedélyezett következő toolok, illetve a releváns kódrészletek. Többfájlos projektnél ehhez még fájllista, függvényvázlat és célzott kódkontextus is tartozik. A modell tehát nem csak promptot kap, hanem egyfajta mérési csomagot, amiből ki kell választania a következő lépést.

A program kimenete több szinten értelmezhető. Egy session végén látható, hogy sikeres volt-e az optimalizálás, milyen patch készült, átmentek-e a tesztek, mennyi lett a baseline és az optimalizált futási idő, illetve mekkora lett a speedup. Az `evaluate` futás végén ezekből aggregált `CSV` és `YAML` fájl készül, plusz egy `report.md` és több diagram. Ezek mutatják például a modellek és prompt pack-ek gyorsulását, a sikeres és sikertelen futások arányát, a toolhasználatot, az LLM hívások számát, a runtime változását és a hardveres metrikák előtte-utána értékeit. Így nem csak az derül ki, hogy egy adott futás jó lett-e, hanem az is, hogy melyik modell és promptstratégia mennyire megbízható ebben a folyamatban.

A program működése röviden úgy épül fel, hogy a CLI kap egy projektet, egy modellt vagy modelllistát, egy prompt pack-et vagy prompt pack listát, illetve a teszteléshez és méréshez szükséges parancsokat. Ezután minden optimalizálási próbához létrehoz egy külön workspace-t a `results/` mappán belül. Ez azért fontos, mert így az AI nem az eredeti fájlokon dolgozik közvetlenül, hanem egy másolaton. Ha a patch rossz, lassabb, vagy elrontja a teszteket, akkor az eredeti projekt nem sérül, a session pedig vissza tud állni az előző biztonságos állapotra.

Egy session elején a rendszer betölti az adott prompt pack-et. A prompt pack több fájlból áll: van egy általános `master.md`, van külön döntési prompt, külön elemző prompt, külön patch-kérő prompt és külön eredményértékelő prompt. A modell minden lépésnél megkapja az aktuális állapotot, az engedélyezett actionöket, a korábbi toolok rövidített eredményét és a mérési adatokat. A válasznak strukturált JSON-nek kell lennie, például meg kell mondania, hogy `run_baseline`, `profile_execution`, `propose_change` vagy `apply_and_verify` legyen a következő lépés. Így a modell nem szabadon szövegel, hanem a program által megadott keretek között hoz döntést.

Az első fontos lépés a baseline mérés. Ilyenkor a program lefuttatja a teszteket, a benchmarkot és ha meg van adva, akkor a hardveres profilt is. A tesztek több ismétléssel futnak, viszont a modell nem kapja meg az összes nyers kimenetet, mert az túl sok token lenne. Ehelyett a program összefoglalót készít, például hány futás ment át, mennyi volt az átlagos futásidő, volt-e hiba, és mennyi volt a benchmark átlaga. Ugyanez igaz a hardveres metrikákra is: a `perf` kimenetből átlagolt cache, branch és L1 jellegű adatok kerülnek be a kontextusba.

Ezután jön a profilozás és a célpontválasztás. Egyfájlos projektnél ez egyszerűbb, mert a modell kevesebb kódot kap. Többfájlos projektnél viszont a program nem próbálja meg egyben betömni az egész projektet a promptba, hanem kompaktabb kontextust készít: fájllistát, AST jellegű vázlatot, fontosabb függvényeket, profilozási részleteket és célzott kódrészleteket ad. Ezzel az volt a cél, hogy a kisebb modellek se vesszenek el a túl nagy kontextusban, a nagyobb modellek pedig jobban tudjanak a tényleges hotspotra koncentrálni.

Ha a modell kiválasztott egy célpontot, akkor a `propose_change` lépésben patch-et kell javasolnia. A program ezt nem fogadja el azonnal. Először eltárolja a javaslatot, majd az `apply_and_verify` lépésben alkalmazza a workspace-ben, lefuttatja a teszteket, és csak akkor megy tovább, ha a kód helyes maradt. Ha a tesztek elbuknak, akkor rollback történik. Ez volt az egyik legfontosabb biztonsági rész, mert több futásnál látszott, hogy egy modell jó irányba indul el, de apró szemantikai hibával vagy rossz patch formátummal elrontaná a programot.

Ha a patch átment a teszteken, akkor a program újraméri az optimalizált kódot. Itt ugyanazok a benchmark és hardveres mérési parancsok futnak, mint baseline-nál, ugyanannyi ismétléssel. Ezután az `evaluate_result` lépés összeveti a baseline és az optimalizált eredményt. Ha a gyorsulás elég jó, vagy a további próbálkozás már nem lenne ésszerű, akkor a session `DONE` állapotba kerül. Ha nincs javulás, vagy elfogyott a budget, akkor a session megáll, és az eredmény `FAILED` vagy nem sikeres optimalizációként kerül a riportba.

Az `evaluate` mód ezt a teljes folyamatot ismétli végig több modellre és prompt pack-re. Minden kombinációról külön session készül, a végén pedig a program összesíti az eredményeket. Ebből jön létre az `aggregated_results.csv`, az `aggregated_results.yaml`, a `report.md` és a `charts/` mappa. Ezekből lehet utána megnézni, hogy melyik modell mennyi toolt hívott, hány LLM hívás kellett neki, sikeres volt-e a patch, milyen gyorsulást ért el, és hogyan változtak a hardveres mutatók.

## A rendszer fő eszközei

| Tool | Mire való |
| --- | --- |
| `inspect_codebase` | A modell kontextust kap a projektről, a fájlokról és a releváns kódrészletekről. |
| `run_baseline` | Lefuttatja az alap teszteket, a benchmarkot és a hardveres méréseket. |
| `profile_execution` | cProfile és Linuxon `perf` alapján megmutatja, hogy hol megy el az idő. |
| `analyze_candidate` | A modell kiválasztja, melyik függvényt vagy fájlt érdemes optimalizálni. |
| `propose_change` | A modell patch-et javasol a kiválasztott célpontra. |
| `apply_and_verify` | A program alkalmazza a patch-et, majd lefuttatja a teszteket. |
| `remeasure` | Újraméri az optimalizált kódot, hogy össze lehessen hasonlítani a baseline-nal. |
| `evaluate_result` | Eldönti, hogy az eredmény elfogadható-e, vagy nem érdemes tovább próbálkozni. |
| `rollback_to_checkpoint` | Hibás vagy lassabb módosításnál visszaállítja a biztonságos állapotot. |

A projektben több promptolási stratégia is található a `prompts/` mappában. Ezek mind ugyanazt az optimalizáló programot használják, csak más módon próbálják rávezetni a modellt a jó döntésre. A `zero_shot` minimális instrukcióval dolgozik, a `few_shot` példák alapján mutatja meg a várt működést, a `knowledge_gen` előbb háttértudást és hipotézist épít, a `hardware_focus` a cache és branch jellegű mérésekre figyel jobban, a `self_refine` saját ellenőrzésre kéri a modellt, a `cot` és a `least_to_most` lépésenkénti gondolkodást használ, a `prompt_chaining` pedig jobban szétválasztja a döntési lépéseket. Ezek mellett szerepel az `agentic` és a `hypothesis_driven` is, ahol már erősebben megjelenik az, hogy a modellnek a program állapotához és a mérési eredményekhez kell igazodnia.

## Kiemelt prompt pack: `hypothesis_driven`

A mérések alapján a `hypothesis_driven` volt az egyik legjobban védhető prompt pack, ezért ezt választottam ki részletesebben. Ennek az a lényege, hogy a modell ne általános optimalizálási ötleteket adjon, hanem mindig fogalmazzon meg egy mérhető hipotézist. Tehát mondja meg, hogy melyik metrikának kell javulnia, miért pont az adott kódrészletet választja, és a patch miért fog ezen segíteni. Ez szerintem jól illik ehhez a programhoz, mert itt amúgy is minden döntés méréshez van kötve.

| Prompt fájl | Mire való |
| --- | --- |
| `master.md` | Beállítja a modell szerepét, az állapotgépet, az engedélyezett actionöket és azt, hogy mérés alapján kell dolgoznia. |
| `decision.md` | Minden lépésnél kiválasztja a következő toolt, de csak érvényes JSON választ adhat. |
| `analyze_candidate.md` | Kiválaszt egy konkrét hotspotot, és ehhez mérhető hipotézist kell adnia. |
| `propose_change.md` | Patch-et kér a célpontra, rövid indoklással és várható hatással. |
| `evaluate_result.md` | Összeveti az elvárt és a mért eredményt, majd eldönti, hogy meg kell-e állni. |
| `config.yaml` | A prompt pack neve, verziója és rövid leírása. |

## Tesztkódok, futtatók és promptok

A mérésekhez két fő tesztprogramot használtam. Az első a [heavy_compute.py](examples/heavy_compute.py), ami egy egyfájlos, számításigényes Python program saját unittest tesztekkel. Ezen jól lehetett mérni, hogy a modellek megtalálják-e az egyértelmű algoritmikus problémát, és tudnak-e úgy gyorsítani rajta, hogy közben a tesztek továbbra is átmenjenek. A második a [complex_pipeline](examples/complex_pipeline) mappa volt, ami már több fájlból álló program. Ennél külön tesztfájl is van: [test_market_sim.py](examples/complex_pipeline/test_market_sim.py). Ezt azért készítettem, mert a valóságban egy optimalizálás ritkán csak egyetlen fájlt érint, és itt már fontosabb volt, hogy a modell értse a fájlok közötti kapcsolatokat is.

A Debianos futtatásokhoz külön shell scriptek készültek. Ezekkel lehetett úgy elindítani a méréseket, hogy ne kézzel kelljen mindig megadni a modelleket, prompt pack-eket, `perf` countereket, ismétlésszámokat és a benchmark parancsokat.

| Script | Mire használtam |
| --- | --- |
| [evaluate_debian_smoke.sh](scripts/evaluate_debian_smoke.sh) | Gyorsabb próbamérésre, hogy egy olcsóbb vagy kisebb futással kiderüljön, működik-e a teljes pipeline. |
| [evaluate_debian_full.sh](scripts/evaluate_debian_full.sh) | Az egyfájlos [heavy_compute.py](examples/heavy_compute.py) teljesebb mérésére, több modellel és több prompt pack-kel. |
| [evaluate_debian_complex.sh](scripts/evaluate_debian_complex.sh) | A többfájlos [complex_pipeline](examples/complex_pipeline) mérésére, a legjobban teljesítő modellekkel és prompt stratégiával. |
| [repeat_unittest_summary.py](scripts/repeat_unittest_summary.py) | Nem shell script, de a futtatók ezt használják arra, hogy a tesztek több ismétlésének eredményéből rövid összefoglaló készüljön. |

A promptok a [prompts](prompts) mappában vannak. A végső heavy mérésben főleg ezek szerepeltek: [zero_shot](prompts/zero_shot), [knowledge_gen](prompts/knowledge_gen), [hardware_focus](prompts/hardware_focus), [hypothesis_driven](prompts/hypothesis_driven), [self_refine](prompts/self_refine) és [few_shot](prompts/few_shot). A komplex többfájlos mérésnél a legerősebb modelleket már a [hypothesis_driven](prompts/hypothesis_driven) prompt pack-kel futtattam, mert az előző eredmények alapján ez illeszkedett a legjobban a mérésvezérelt működéshez. A részletesebb, diagramokkal alátámasztott feldolgozás a [debian-combined-llm-prompt-analysis](docs/experiments/debian-combined-llm-prompt-analysis) mappában található, a heavy futás külön elemzése pedig itt: [debian-full-heavy-1778099536167691431](docs/experiments/debian-full-heavy-1778099536167691431).

## Eredmények

A teszteket Debian 12-es rendszeren futtattam le, mert a hardveres mérésekhez Linuxos `perf` countereket használtam. Az OpenRouteres modellek természetesen külső szolgáltatáson keresztül futottak, a self-hostolt Qwen 2.5 Coder 7B modell pedig helyben, egy NVIDIA P104-100 videókártyán ment, 8 GB VRAM-mal. Ezt azért fontos külön leírni, mert a lokális modellnél nem csak maga a modell számít, hanem az is, hogy milyen hardveren fut, mennyi memóriája van, és ez mennyire tudja kiszolgálni az optimalizálási sessionöket.

A végső teszteknél kétféle kódot használtam. Az `examples/heavy_compute.py` egy egyfájlos, direkt számításigényes példa volt, ahol jól látszott, hogy a modellek megtalálják-e a domináns algoritmikus hibát. Itt a legerősebb modellek szinte mindig a `segmented_prefix_sums_slow` részt találták meg, és az O(n²) jellegű számítást O(n) futó összeges megoldásra cserélték. Emiatt több modellnél is 7-8x körüli gyorsulás jött ki, ami elsőre furcsának tűnhet, de valójában azt mutatja, hogy ebben a kódban volt egy nagyon erős, egyértelmű hotspot.

![Modellek gyorsulása benchmarkonként](docs/experiments/debian-combined-llm-prompt-analysis/charts/speedup_by_dataset_model.png)

![Prompt pack-ek összehasonlítása a heavy benchmarkon](docs/experiments/debian-combined-llm-prompt-analysis/charts/heavy_prompt_speedup_heatmap.png)

![Patch próbálkozások kimenetele modellenként](docs/experiments/debian-combined-llm-prompt-analysis/charts/patch_status_by_model.png)

A második méréshez készítettem egy többfájlos `examples/complex_pipeline` példát is. Ez már nehezebb volt, mert több fájl, több wrapper függvény és több kisebb hotspot volt benne. Itt jobban kijött, hogy nem elég csak a legnagyobb kumulatív futásidőt nézni, mert az néha csak azt mutatja, hogy melyik magasabb szintű függvény hív sok másikat. A jobb optimalizációhoz a tényleges self-time hotspotot kellett megtalálni, például a `customer_recent_totals` jellegű részeket.

A modellek viselkedése alapján az derült ki, hogy a nagyobb modellek előnye nem feltétlenül az volt, hogy teljesen más ötletet találtak, hanem az, hogy stabilabban vitték végig ugyanazt a jó mérnöki döntést. A Gemini 3.1 Pro, a GPT-OSS 120B és a GPT-5.3 Codex jól működtek a rendszerrel, a self-hostolt Qwen 2.5 Coder 7B viszont sokszor közel volt a jó irányhoz, de a patch formátuma vagy a kód szemantikája nem volt elég stabil. Ez hasznos tapasztalat volt, mert így látszott, hogy egy lokális vagy olcsóbb modell nem biztos, hogy a teljes folyamatban is olcsóbb, ha sok sikertelen próbálkozást termel.

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

## Tanulságok

A legfontosabb technikai tanulság nekem az volt, hogy az AI-alapú kódoptimalizálás akkor kezd igazán használható lenni, ha nem csak promptolásból áll. A modell önmagában tud mondani jó ötletet, de ettől még nem biztos, hogy a kód helyes marad, vagy hogy tényleg gyorsabb lesz. Emiatt kellett köré mérés, tesztelés, rollback és újramérés. Így a modell javasol, de a program dönt arról, hogy a javaslat elfogadható-e.

Az is látszott, hogy a modellek összehasonlításánál nem csak a végső speedup számít. Egy egyszerűbb benchmarkon több modell is ugyanarra a 7-8x gyorsításra jutott, mert a legnagyobb hiba nagyon egyértelmű volt. Ilyenkor a különbség inkább abban jelenik meg, hogy mennyire kevés hibás JSON-t adnak, mennyire jó patch-et készítenek, és mennyire tartják be az állapotgép szabályait. Tehát nem csak az a kérdés, hogy "megtalálta-e az ötletet", hanem az is, hogy végig tudta-e vinni úgy, hogy a rendszer elfogadja.

A promptstratégiáknál az volt a tanulság, hogy azok működtek jobban, amelyek illeszkedtek a program működéséhez. A `hypothesis_driven` azért volt jó, mert ugyanarra kényszerítette a modellt, amit a rendszer is elvárt: mérhető állítás, konkrét célpont, ellenőrzött patch és döntés az eredmény alapján. Egy nagyon egyszerű esetben a `zero_shot` is tud jó lenni, de többfájlos vagy bizonytalanabb projektnél sokkal fontosabb, hogy a prompt ne csak általános instrukció legyen, hanem a program tooljait és állapotait is értse a modell.

A hardveres méréseknél külön érdekes volt, hogy a cache hit-rate önmagában nem mindig jó sikerességi mutató. Volt olyan futás, ahol a cache arány kicsit romlott, de a program mégis sokkal gyorsabb lett, mert egyszerűen sokkal kevesebb munkát végzett. Emiatt a runtime lett az elsődleges metrika, a cache, L1, branch és LLC adatok pedig inkább magyarázó metrikák. Az LLC counterekkel az is kiderült, hogy Linuxon sem garantált, hogy minden hardveres számláló elérhető, ez függ a géptől, kerneltől és virtualizációtól is.

A többfájlos példánál az volt a legfontosabb, hogy a profilozási eredményeket nem szabad vakon olvasni. A cProfile kumulatív ideje néha olyan függvényre mutat, ami csak meghív sok másik drága részt, de nem ott érdemes optimalizálni. Ilyenkor a modellnek és a programnak is jobb kontextus kell: fájlok közötti kapcsolat, self-time, hívási lánc és célzott kódrészlet. Ezért került bele később az is, hogy nagyobb projektnél ne egyben kapja meg az egész kódot, hanem a program logika alapján tördelje és célzottabban adja oda a kontextust.

Összességében szerintem a feladat lényege az lett, hogy az AI nem egy varázslatos optimalizáló, hanem egy mérnöki folyamat egyik eleme. A jó eredményt nem csak a modell adja, hanem az, hogy van körülötte mérés, guardrail, teszt, rollback, budget és riportolás. Így már nem csak az látszik, hogy "az AI átírt valamit", hanem az is, hogy mit változtatott, miért, hányszor próbálkozott, sikeres volt-e, és mérhetően mennyit javult tőle a program.

Részletesebb elemzés és további diagramok: [docs/experiments/debian-combined-llm-prompt-analysis/README.md](docs/experiments/debian-combined-llm-prompt-analysis/README.md)

Technikai használati útmutató a CLI-hez és a régi részletesebb architekturális leíráshoz: [USERMANUAL.md](USERMANUAL.md)

## A program elkészítéséből származó tapasztalataim

A program elkészítéséhez többféle modellt és többféle felületet is kipróbáltam: webes ChatGPT-t, CLI alapú eszközöket és desktopos Codex használatot is. A tervezéshez főleg a webes ChatGPT-t használtam GPT-5.4 modellel, mert nagyobb kontextusban kényelmesebb volt vele végiggondolni a teljes követelményrendszert. Először csak felvázoltam neki, hogy milyen programot szeretnék készíteni, hogyan képzelem el a működését, milyen mérések kellenek, és milyen módon szeretném összehasonlítani a modelleket. Ezután lényegében közösen finomítottuk a tervet, majd a beszélgetés végén megírattam vele egy összefüggő, véglegesebb követelményrendszert.

Ezt a követelményrendszert először GeminiCLI-nak adtam oda, automatikus modellválasztással, ahol Gemini 3.1 Pro és Gemini 3 Flash is szerepelt. Itt azt tapasztaltam, hogy maga a feladat és a kontextus egyben túl nagy volt: a kért rendszernek csak egy részét valósította meg, és az elkészült részek sem feltétlenül úgy működtek, ahogy elvártam. Emiatt ugyanazt a követelményrendszert később Codexnek adtam be, ahol már GPT-5.4 és GPT-5.5 modelleket is használtam. A Codex először készített egy checklistet arról, hogy milyen lépésekre kell bontani a megvalósítást, majd létrehozott egy demó programot. Ez az első változat még messze nem volt tökéletes, de már futtatható volt, így volt egy alap, amit lehetett mérni, javítani és továbbépíteni.

Nekem ebből az lett az egyik legerősebb tapasztalatom, hogy egy nagyobb fejlesztési feladatnál sokkal jobban működik, ha először nem azonnal implementációt kérek, hanem csak tervet. Ha a modell előbb megtervezi a megoldást, én azt átnézem, pontosítom, és csak utána kérem a megvalósítást, akkor sokkal kevesebb félreértés történik. Amikor rögtön nagy, több részből álló feladatot adtam be, gyakrabban előfordult, hogy a modell kihagyott részeket, rossz helyen javított, vagy nem azt tekintette fő feladatnak, amit én. Amikor viszont külön választottam a tervezést, a megvalósítást és az ellenőrzést, akkor a végeredmény stabilabb lett, és kevesebbet kellett utólag korrigálni.

A korai, még nem jól működő iránynál az is kiderült, hogy a jelenlegi Codex nem kezeli jól, ha egyszerre túl sok, egymástól eltérő szerepet kap. 2026.03.25 körül próbáltam úgy dolgozni vele, hogy közben jegyzőkönyvet is vezessen a tapasztalatokról, készítsen tesztprogramokat, és magát az optimalizáló keretrendszert is fejlessze. Ekkor sokszor összekeverte, hogy mi az aktuális fő feladat: ha például egy hibát a programban akartam kijavítani, néha úgy értelmezte, hogy a tesztet kell átírni, vagy csak a jegyzőkönyvbe kell beírni a problémát. Ebből az következett, hogy egy ilyen projektnél érdemesebb a feladatokat tisztábban szétválasztani, vagy akár külön agenteket használni külön szerepekre.

Ugyanebben a korai szakaszban az egységtesztek hibáinak elemzése sem ment mindig jól. Amikor az optimalizálás után a tesztek nem futottak le helyesen, és azt kértem, hogy nézze meg, mi lehet az oka, gyakran először a tesztek átírását javasolta, nem pedig azt kereste, hogy a program módosítása rontotta-e el a viselkedést. Csak akkor jutott közelebb a jó javításhoz, amikor sokkal pontosabban leírtam, hogy nem a tesztet akarom hozzáigazítani a hibás kódhoz, hanem a kódot kell úgy javítani, hogy a meglévő tesztek maradjanak érvényesek. Volt olyan is, hogy kitalált egy módszert, amitől a program már lefutott, de közben valójában nem végzett érdemi LLM-alapú vagy heurisztikus optimalizálást. Ez jól megmutatta, hogy az AI-nak nem elég azt mondani, hogy "javítsd ki", hanem nagyon pontosan meg kell határozni, milyen viselkedés számít elfogadható javításnak.

Egy másik tanulság az volt, hogy a modell néha akkor is kerülő megoldást választ, ha ezt külön kérem, hogy ne tegye. Például volt olyan eset, amikor azt kértem, hogy ne új flag bevezetésével kerülje meg a hibát, hanem magát a hibás működést javítsa ki, mégis új flaget hozott létre. Ezért került később nagyobb hangsúly a guardrailekre, a pontos tool szerződésekre és arra, hogy a rendszer ne csak elfogadja a modell javaslatát, hanem verifikálja is. A végső programban pont ezért lett fontos, hogy a modell patch-e csak akkor számít sikeresnek, ha a tesztek és az újramérés alapján is elfogadható.

2026.03.26 körül a GeminiCLI-val kapcsolatban is volt egy érdekes tapasztalatom. Korábban többször előfordult, hogy 20-30 percig nem válaszolt, és emiatt félbeszakítottam a próbálkozást. Később viszont meglepően jól működött olyan feladatoknál, ahol egy prompt után egy konkrét feature-t kellett megvalósítania, majd teszteket írnia hozzá, és addig javítania, amíg működött. Ugyanakkor néha így is véletlenszerűen leállt munka közben. Emiatt végül nem egyetlen eszközre építettem a teljes folyamatot, hanem több modellt és több futtatási módot próbáltam ki, és abból vontam le a következtetéseket.

## Ellenőrzés

```bash
PYTHONPATH=src .venv/bin/python -m compileall -q src/optimizer
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m optimizer.cli doctor
```
