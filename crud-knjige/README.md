# Evidencija knjiga

Drugi Docker zadatak: REST API za CRUD nad tabelom `knjige` u PostgreSQL bazi. Swagger UI je na `/docs`. Aplikacija i baza imaju zasebne Docker slike.

## Pokretanje

U folderu `crud-knjige`:

```bash
docker compose up --build -d
docker compose ps
```

Otvori port 8000 u Codespaces kartici **Ports** i dodaj `/docs` na kraj prikazane adrese. Na Swagger stranici isprobaj `POST /knjige`, `GET /knjige`, `PUT /knjige/{knjiga_id}` i `DELETE /knjige/{knjiga_id}`.

Primer za POST i PUT:

```json
{"naslov":"Na Drini ćuprija","autor":"Ivo Andrić","godina":1945}
```

Posle dodavanja koristi ID iz odgovora za PUT i DELETE. `GET /knjige` posle brisanja više ne prikazuje obrisanu knjigu. Baza ostaje sačuvana u Docker volume-u `podaci_knjige` i nakon `docker compose down`.

## Objavljivanje dve slike

Prijavi se na svoj Docker Hub nalog, pa u ovom folderu izvrši:

```bash
docker login
docker compose build
docker push bojana0606/crud-knjige-api:1.0
docker push bojana0606/crud-knjige-db:1.0
```

Proveri da oba repozitorijuma imaju javnu vidljivost na Docker Hub profilu `bojana0606`. Lozinku ne upisuj kao vidljiv tekst u terminal.

Za zaustavljanje koristi `docker compose down`. Ne koristi `docker compose down -v` ako želiš da sačuvaš podatke.

Ovaj primer koristi demonstracionu lozinku namenjenu samo lokalnoj vežbi.
