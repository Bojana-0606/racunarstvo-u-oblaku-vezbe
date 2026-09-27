# Treći zadatak: CWL regresija nad Boston Housing CSV podacima

Ulazi su CSV, tačan naziv ciljne kolone i procenat trening skupa (celi broj 1–99). Izlazi su `metrics.json` i `preprocessing_report.json`. Tok ima tačno dva koraka: `clean_data` i `train_model`. Svaki korak u `DockerRequirement` koristi javnu sliku sa profila `bojana0606`.

## Priprema podataka

CSV `data/HousingData.csv` u ovoj kopiji dolazi iz arhive koju je korisnica preuzela sa [zadatog Kaggle skupa](https://www.kaggle.com/datasets/altavish/boston-housing-dataset). Provereno zaglavlje sadrži kolonu `MEDV`, koja je primer cilja u `job.example.yml`. Ako želiš drugi numerički cilj, promeni `target`; ako koristiš drugi CSV, promeni njegov `path`.

## Pravljenje i objavljivanje slika

U folderu `cwl-boston-housing`:

```bash
docker build -t bojana0606/cwl-boston-preprocess:1.0 ./preprocess
docker build -t bojana0606/cwl-boston-model:1.0 ./model
docker login
docker push bojana0606/cwl-boston-preprocess:1.0
docker push bojana0606/cwl-boston-model:1.0
```

Proveri da su obe slike `Public` na Docker Hubu. Lozinku naloga ne upisuj kao vidljiv tekst u terminal. Za dokaz povlačenja javnih slika, nakon push komandi na istom računaru možeš obrisati samo ove dve *lokalne* slike, pa pokrenuti CWL:

```bash
docker image rm bojana0606/cwl-boston-preprocess:1.0 bojana0606/cwl-boston-model:1.0
```

## Pokretanje

Na računaru ili u Codespace okruženju gde rade Docker i Python:

```bash
python -m pip install cwltool
mkdir -p results
cwltool --outdir results workflow.cwl job.example.yml
cat results/metrics.json
cat results/preprocessing_report.json
```

`cwltool` po `dockerPull` oznaci povlači obe slike sa Docker Huba ako lokalno ne postoje. Ne uključivati opciju `--no-container`, jer oba koraka moraju da rade u Docker okruženju. CSV je ulazni fajl, a `results/metrics.json` konačan rezultat.

## Šta se računa

Prvi korak deli redove na trening i test (`random_state=42`). Redovi bez poznate ciljne vrednosti se uklanjaju jer se bez nje ne može oceniti model. Ostale praznine popunjava prosekom odgovarajuće kolone iz **trening skupa**. Outlier je trening red sa bar jednom ulaznom numeričkom vrednošću izvan 1.5 × IQR opsega te kolone. Takvi redovi se uklanjaju samo iz treninga. Test redovi se ne uklanjaju, da merenje ostane nepristrasno.

Drugi korak trenira `RandomForestRegressor` sa 100 stabala i računa metrike isključivo na test skupu:

- `RMSE = sqrt(mean((y_test - y_pred)^2))`, u jedinicama ciljne kolone.
- `PRMSE_percent = 100 × RMSE / mean(abs(y_test))`; ova verzija procentualnog RMSE je **izričito definisana za ovaj projekat**, pošto skraćenica PRMSE može imati više definicija. Ako je imenilac nula, rezultat je `null`.
- `MAE = mean(abs(y_test - y_pred))`.
- `R2` je koeficijent determinacije.

Ne navoditi brojčane rezultate pre pokretanja nad stvarnim Kaggle CSV fajlom. Vrednosti zavise od ulaza i izabranog procenta treninga.
