# Scatter CWL k-fold validacija Boston Housing

Ulazi: `csv`, `target`, `k`. Primer: `data/HousingData.csv`, `MEDV`, `5`.

`folds.cwl` priprema k parova trening/test CSV fajlova (prosek i IQR pragovi računaju se samo iz trening dela svakog folda). `workflow.cwl` koristi `ScatterFeatureRequirement`, `scatter: [train, test]` i `scatterMethod: dotproduct`, pa je svaki fold zaseban CWL posao. `model.cwl` koristi već javnu sliku `bojana0606/cwl-boston-model:1.0` iz prethodnog zadatka. `aggregate.cwl` objedinjuje metrike i računa aritmetički prosek i uzoračku standardnu devijaciju. Izlazi su `summary.json`, niz pojedinačnih `metrics.json` fajlova i `folds_report.json`.

Iz korena ovog foldera:

```bash
docker build -t bojana0606/cwl-boston-folds:1.0 ./folds
docker build -t bojana0606/cwl-boston-aggregate:1.0 ./aggregate
docker login
docker push bojana0606/cwl-boston-folds:1.0
docker push bojana0606/cwl-boston-aggregate:1.0
cwltool --validate workflow.cwl
mkdir -p results .cwl-tmp
cwltool --tmpdir-prefix "$PWD/.cwl-tmp/" --tmp-outdir-prefix "$PWD/.cwl-tmp/" --outdir results workflow.cwl job.example.yml
cat results/summary.json
```

Slike u `dockerPull` se zaista povlače sa Docker Huba ako nisu u lokalnom kešu. Pre objavljivanja slika moguće je lokalno testiranje Python skripti i CWL sa `--no-container` samo ako su odgovarajuće Python biblioteke instalirane. `results/` je lokalni izlaz i nije automatski objavljen na GitHubu.

CSV: https://www.kaggle.com/datasets/altavish/boston-housing-dataset
CWL scatter dokumentacija: https://www.commonwl.org/user_guide/en/topics/workflows.html
