# Guia: executar AgentZon en mode distribuït

Aquesta guia explica com arrencar el sistema AgentZon repartit entre diversos ordinadors
de la mateixa xarxa local (laboratori, demo del professor, etc.).

---

## 1. Idea general

- Hi ha **12 agents** independents (cada un és un servidor Flask).
- Tots es descobreixen via l'**Agent Directory** (port 9000).
- Cada agent corre en **un PC diferent** (o dos agents al mateix PC si només teniu 11
  ordinadors).
- Només cal configurar **una IP compartida**: la del PC on corre el Directory.
- Cada PC **detecta sol** la seva IP local en arrencar el seu agent.

```
  PC Directory (10.10.43.1)          PC Cobrador (10.10.43.2)
  ┌─────────────────────┐            ┌─────────────────────┐
  │ agent_directory     │◄───────────│ agent_cobrador        │
  │ :9000 /Register     │  registre  │ :9005 /comm           │
  └─────────┬───────────┘            └─────────────────────┘
            │
            │  tots els agents es registren aquí
            ▼
     (cercador, compra, centres, ...)
```

---

## 2. Requisits per a cada PC

1. **Codi**: clona o copia la carpeta `AgentZon/` (o tot el repositori).
2. **Entorn virtual**:
   ```bash
   cd AgentZon
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Dades**: la carpeta `data/` ha d'existir (ve amb el repo; si cal, regenera-les):
   ```bash
   .venv/bin/python -m services.bootstrap --data-dir data --product-count 24 --seed 21
   ```
4. **Xarxa**: tots els PCs a la **mateixa LAN** (Wi‑Fi o cable del laboratori).
5. **Firewall**: permet connexions entrants als ports 9000–9012.
6. **Fitxer compartit**: el mateix `distributed.env` a totes les màquines.

---

## 3. Configuració (`distributed.env`)

Des de `AgentZon/`:

```bash
cp distributed.env.example distributed.env
```

Edita **només** la IP del PC que farà de Directory:

```bash
DIRECTORY_HOST=10.10.43.1
DIRECTORY_PORT=9000
```

Copia aquest fitxer **idèntic** a tots els ordinadors (USB, git, AirDrop, etc.).

### Opcional: forçar la IP local

Si la detecció automàtica falla (VPN, diverses interfícies de xarxa):

```bash
LOCAL_HOST=10.10.43.5
```

Comprova quina IP detecta el PC:

```bash
./run_distributed_agent.sh --local-ip
```

---

## 4. Assignació d'agents (12 agents, 11 PCs)

| Agent | Comanda | Port | Interfície web |
|-------|---------|------|----------------|
| Directory | `directory` | 9000 | — (`/Register`) |
| Cobrador | `cobrador` | 9005 | — |
| Opinador | `opinador` | 9004 | — |
| Retornador | `retornador` | 9009 | — |
| Transportista ràpid | `transport_fast` | 9010 | — |
| Transportista econòmic | `transport_economy` | 9011 | — |
| Centre BCN | `centre_bcn` | 9003 | — |
| Centre Girona | `centre_gi` | 9007 | — |
| Centre Tarragona | `centre_tgn` | 9008 | — |
| Venedor extern | `venedor_extern` | 9012 | `/iface` |
| Compra | `compra` | 9002 | — |
| Cercador | `cercador` | 9001 | `/iface` (cerca/compra) |

Llista completa al terminal:

```bash
./run_distributed_agent.sh --list
```

**Amb 11 PCs:** al mateix ordinador executa dos agents en **dues terminals** (p. ex.
`transport_fast` i `transport_economy`).

---

## 5. Arrencada manual (recomanada al laboratori)

Cada persona, al seu PC, des de `AgentZon/`:

```bash
chmod +x run_distributed_agent.sh    # només la primera vegada
./run_distributed_agent.sh <agent>
```

### Ordre d'arrencada

Espereu uns **3–5 segons** entre màquines perquè el Directory estigui llest abans dels
registres.

1. `directory` — **sempre el primer**, al PC de `DIRECTORY_HOST`
2. `cobrador`
3. `opinador`, `retornador`
4. `transport_fast`, `transport_economy`
5. `centre_bcn`, `centre_gi`, `centre_tgn`
6. `venedor_extern`
7. `compra`
8. `cercador` — el darrer (exposa la UI principal)

### Exemple

**PC del Directory** (`10.10.43.1`):

```bash
./run_distributed_agent.sh directory
```

**PC del Cobrador**:

```bash
./run_distributed_agent.sh cobrador
```

El script mostra:

```
=== AgentZon distribuït: cobrador ===
Màquina ( --publish-host ): 10.10.43.2
Escolta ( --host ):         0.0.0.0
Directory ( --directory-host ): 10.10.43.1:9000
```

- `--host 0.0.0.0` → accepta connexions de la xarxa.
- `--publish-host` → IP que queda registrada al Directory (la d'aquest PC).

---

## 6. Comprovar que tot funciona

### Al PC del Directory

```bash
lsof -nP -iTCP:9000 -sTCP:LISTEN
```

Ha de mostrar un procés en escolta.

### Des d'un altre PC

```bash
curl -v --max-time 3 "http://10.10.43.1:9000/Register"
```

Si respon (fins i tot amb cos buit), la xarxa és correcta.

### Després d'arrencar un agent

Al log hauria d'aparèixer el registre al Directory. Si falla amb `Connection refused`:

- El Directory no està en marxa o `DIRECTORY_HOST` és incorrecte.
- El firewall bloqueja el port 9000.

Si el registre funciona però després ningú troba l'agent:

- Comprova `./run_distributed_agent.sh --local-ip` (no ha de ser `127.0.0.1`).
- Afegeix `LOCAL_HOST=<ip_lan>` a `distributed.env`.

---

## 7. Interfícies web

Quan tots els agents estiguin actius:

| URL | Descripció |
|-----|------------|
| `http://<ip_pc_cercador>:9001/iface` | Cerca i compra de productes |
| `http://<ip_pc_venedor>:9012/iface` | Registre de productes de venedors externs |

Substitueix `<ip_pc_cercador>` per la IP real del PC on corre el Cercador (la que surt
amb `--local-ip` en aquella màquina).

---

## 8. Scripts auxiliars

### Generar un script per agent (`generate_node_scripts.sh`)

Útil per repartir un fitxer `.sh` a cada company:

```bash
./generate_node_scripts.sh
```

Crea `distributed/nodes/start_<agent>.sh`. Cada persona executa només el seu:

```bash
bash distributed/nodes/start_cobrador.sh
```

### Desplegament centralitzat per SSH (`deploy_distributed.sh`)

Només si un PC pot fer SSH sense contrasenya a tots els altres.

**Fitxers extra:**

```bash
cp deploy.hosts.example deploy.hosts
# Edita deploy.hosts: una línia agent=ip per cada PC
```

A `distributed.env`:

```bash
SSH_USER=el_teu_usuari
REMOTE_AGENTZON_DIR=/ruta/absoluta/al/AgentZon
```

**Comprovacions abans de desplegar:**

```bash
./deploy_distributed.sh --check         # prova SSH
./deploy_distributed.sh --check-setup   # SSH + projecte + .venv
./deploy_distributed.sh --dry-run       # previsualitza comandes
```

**Arrencar / aturar:**

```bash
./deploy_distributed.sh                 # arrenca tots en ordre
./deploy_distributed.sh --stop          # atura agents remots
./deploy_distributed.sh cobrador          # només un agent
```

**SSH manual (un sol PC):**

```bash
ssh -o ConnectTimeout=5 usuari@10.10.43.2 'echo OK && whoami && hostname'
```

L'usuari SSH és el compte amb què inicies sessió al PC remot (`whoami` en aquell
ordinador).

---

## 9. Aturar els agents

### Al PC local

`Ctrl+C` a la terminal on corre l'agent, o:

```bash
pkill -f '[Pp]ython.*-m agents\.agent_' 2>/dev/null || true
```

### Tots els ports (un sol PC)

```bash
for port in 9000 9001 9002 9003 9004 9005 9006 9007 9008 9009 9010 9011 9012; do
  lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null
done
```

### Remot (des del PC central)

```bash
./deploy_distributed.sh --stop
```

---

## 10. Resolució de problemes

| Símptoma | Causa habitual | Solució |
|----------|----------------|---------|
| `Connection refused` a `DIRECTORY_HOST:9000` | Directory no arrencat o IP incorrecta | Arrenca `directory` primer; verifica `DIRECTORY_HOST` |
| `Connection refused` des d'un altre PC | Firewall o Directory només a `127.0.0.1` | Usa `./run_distributed_agent.sh` (escolta a `0.0.0.0`) |
| Registre amb `127.0.0.1` al missatge RDF | IP local mal detectada | `LOCAL_HOST=<ip_lan>` a `distributed.env` |
| `Address already in use` | Agent ja en execució | Atura el procés (secció 9) |
| Un agent no el troben els altres | No registrat al Directory | Comprova logs; espera que el Directory estigui actiu |
| SSH `Permission denied` | Usuari o clau incorrectes | `ssh-copy-id usuari@ip` |
| `--check-setup` diu `MISSING_VENV` | Falta entorn virtual al PC remot | `python3 -m venv .venv && pip install -r requirements.txt` |

---

## 11. Resum ràpid (checklist demo)

- [ ] `distributed.env` amb `DIRECTORY_HOST` correcte, copiat a tots els PCs
- [ ] `.venv` i `data/` a cada màquina
- [ ] Cada persona sap quin agent li correspon (`--list`)
- [ ] Directory arrencat **primer**
- [ ] Resta d'agents en ordre, amb uns segons d'espera
- [ ] `curl http://<DIRECTORY_HOST>:9000/Register` funciona des d'un altre PC
- [ ] UI: `http://<ip_cercador>:9001/iface`

---

## 12. Fitxers relacionats

| Fitxer | Funció |
|--------|--------|
| `distributed.env.example` | Plantilla de configuració (copia a `distributed.env`) |
| `run_distributed_agent.sh` | Arrenca un agent al PC actual |
| `deploy.hosts.example` | Plantilla per SSH (copia a `deploy.hosts`) |
| `deploy_distributed.sh` | Desplegament/aturada remota per SSH |
| `generate_node_scripts.sh` | Genera scripts per repartir manualment |
| `run_agents.sh` | Mode local (tot a un sol Mac, `127.0.0.1`) |

Per més context del projecte, vegeu [`README.md`](../README.md) i
[`GUIA_NOU_INTEGRANT.md`](Justificacions/GUIA_NOU_INTEGRANT.md).
