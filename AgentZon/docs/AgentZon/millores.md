# Optimized Prompt for Multi-Agent System Refactoring

**Role:** You are an expert Python Developer and Knowledge Engineer specialized in Multi-Agent Systems (MAS) and Semantic Web technologies.

**Task:** Refactor, improve, and document a MAS project (AgentZon), including the codebase and the OWL/RDF ontology.

---

## 1. Code Refactoring & Improvements

### Global Rules:
* **Original Credits:** Maintain the `@author: javier` annotation in all files under `/AgentUtil`, as they belong to the original author.
* **Delivery Phases:**
    * **Phase 2 (Current):** DO NOT remove unused files or functions in `/AgentUtil`.
    * **Final Phase:** Clean up and remove all unused code once the full system is complete.

### Specific Technical Tasks:
* **Hostname Logic:** In `/AgentZon/AgentUtil/Util.py`, the function `gethostname()` is currently unused. Update all agents so that hostname selection follows this logic:
    ```python
    if args.open is None:
        hostname = '0.0.0.0'
    else:
        hostname = socket.gethostname()
    ```
* **Code Centralization:** Refactor the code to extract and centralize common functionality into reusable functions.
* **Agent Class Evaluation:** Review all `agent_*.py` files. Most files define a class and then create the agent using:
    `agent = build_agent("CercadorAgent", "Cercador", args.port, host=args.host)`
    * **Requirement:** Evaluate if the class definition is necessary. If it is not used, remove the class definition from all agents to simplify the code.

---

## 2. Code Documentation
Once the refactoring is complete:
* **Headers:** Add headers to all `.py` files explaining their purpose.
* **Internal Structure:** Add comments and separators to clearly structure the code:
    * Agent attributes
    * Logic sections
    * Communication handling
* **README.md:** Create a `README.md` including:
    * Project structure
    * Execution guide
    * `requirements.txt`
    * Instructions to create and use a virtual environment (`.venv`).

---

## 3. Ontology Design (RDF/OWL)
The current ontology is minimal (only 2 relationships and no attributes). It must be expanded significantly using Protégé.

* **Language:** Add descriptions in **Catalan** to the main concepts.
* **Hierarchy:** Organize concepts hierarchically (e.g., `Actor` -> `Usuari`, `VenedorExtern`, `Transportista`, `Banc`).
* **Communication Structure:** Define a specific taxonomy:
    * `Comunicacio`
        * `Accio`
        * `Resposta`
* **Scope:** The ontology must represent the **ENTIRE** system (including suggestions, returns, etc.), not just implemented features.
* **Attributes:** Define attributes for each concept with types (`string`, `int`, `Date`, etc.). Cardinalities are not required.
* **Integration:** Ensure that all implemented agent actions use concepts defined in the ontology.

---

## 4. Final Documentation
Once everything is completed, document:
* The ontology design.
* The implementation of at least the 6 core agents.
* **Emphasis:** Detailed communication between agents and interaction with external actors.
