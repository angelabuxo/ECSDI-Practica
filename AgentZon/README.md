Estructura de Carpetas

AgentZon /

main.py: El punto de entrada del sistema. Su función es inicializar el entorno de agentes (el contenedor), crear las instancias de cada agente (Cercador, Compra) y mantener el sistema en ejecución.

ontologia/
AgentZonOntology.owl: El núcleo del conocimiento. Contiene la jerarquía de clases (Producte, Categoria), las propiedades (téPreu, téMarca) y los individuos (los productos reales). Es un modelo iterativo que crece con el sistema.

documentation/: Contiene la documentación técnica autogenerada.

index.html: Documentación en formato W3C generada con pylode.

grafo.png: Representación visual de la ontología generada con owl2plot.

protocolos/
Esta carpeta define el "idioma" y los "formularios" que usan los agentes para hablar entre ellos.

cerca.py: Define la estructura de los mensajes de búsqueda. Incluye la clase MostrarCerca, que dicta qué campos debe recibir el usuario cuando el Agent Cercador devuelve resultados.

compra.py: Define la estructura para las transacciones. Incluye la clase ConfirmarCompra, que asegura que los mensajes de éxito o error en el pedido sigan un formato estándar.

agentes/
Aquí reside la lógica de comportamiento (los "cerebros" del sistema).

agent_cercador.py: Implementa el "Pla de cerca". Su responsabilidad es recibir peticiones, realizar consultas SPARQL o filtrados sobre la ontología y devolver los resultados.

agent_compra.py: Implementa la lógica de pedido. Verifica la disponibilidad del producto en la ontología y gestiona la confirmación del pedido simple.

utils/
interfaz.py: Contiene funciones de utilidad para la interacción con el usuario. Centraliza la forma en que se imprimen las tablas de productos y cómo se solicitan los datos por consola, asegurando una estética coherente en todos los agentes.