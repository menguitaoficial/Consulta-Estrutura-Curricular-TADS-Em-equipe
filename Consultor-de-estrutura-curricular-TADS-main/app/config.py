import os

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://tads:tads@localhost:5432/tads")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "tads")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "tads12345")
CURSOS_DIR = os.getenv("CURSOS_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "cursos"))
