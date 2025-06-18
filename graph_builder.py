# graph_builder.py

import json
import os
import warnings
from neo4j import GraphDatabase, Auth
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Union
from enum import Enum

# --- Configuration ---
### --- CHANGE --- ###
# Moved hardcoded credentials to environment variables for security and flexibility.
# Users should set these variables in their environment or a .env file.
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
SEMANTIC_MODEL_DIR = "semantic_models"

# Suppress only deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

#region --- Data Classes (No changes, they are well-defined) ---
@dataclass
class ServiceEndpoint:
    name:str
    endpoint: str

@dataclass
class Controller:
    name: str
    http_call_type: str

@dataclass
class ProjectIRReport:
    name:str
    package_references: Optional[List[str]] = field(default_factory=list)

@dataclass
class VariableType:
    name:str
    type: str

@dataclass
class ExternalCall:
    destination_method: str
    destination_class: str

@dataclass
class MethodDetail:
    method_name: str
    method_source_code: str
    method_argument_type: Optional[List[VariableType]] = field(default_factory=list)
    method_return_type: Optional[str] = None
    local_variable_types: Optional[List[VariableType]] = field(default_factory=list)
    external_calls: Optional[List[ExternalCall]] = field(default_factory=list)

@dataclass
class ClassDetail:
    class_name: str
    file_path: str
    class_source_code: str
    methods: Optional[List[MethodDetail]] = field(default_factory=list)
    inherits: Optional[str] = None
    properties: Optional[List[VariableType]] = field(default_factory=list)
    stored_procedure: Optional[List[str]] = field(default_factory=list)
    external_rest_call: Optional[List[ServiceEndpoint]] = field(default_factory=list)

@dataclass
class RepositoryDetails:
    name:str
    controllers: List[Controller]
    class_details: List[ClassDetail]
    dependent_repositories: Optional[List[str]] = field(default_factory=list)

@dataclass
class GraphNode:
    name: str
    type: str

@dataclass
class ClassNode(GraphNode):
    file_path: str= ""
    source: str= ""
    type: str = "Class"
    ds: bool = False

@dataclass
class MethodNode(GraphNode):
    source: str= ""
    return_type: str = ""
    type: str = "Method"

@dataclass
class VarNode(GraphNode):
    type: str = "Variable"

@dataclass
class RepoNode(GraphNode):
    type: str = "Repository"

@dataclass
class StoredProcedureNode(GraphNode):
    type: str = "StoredProcedure"

@dataclass
class ControllerNode(GraphNode):
    type: str = "Controller"

class RelationshipType(Enum):
    DEPENDS_ON = "DEPENDS_ON"
    HAS_ROUTES = "HAS_ROUTES"
    HAS_CLASSES = "HAS_CLASSES"
    HAS_METHOD = "HAS_METHOD"
    HAS_VARIABLES = "HAS_VARIABLES"
    CALLS_SP = "CALLS_SP"
    CALLS_METHOD = "CALLS_METHOD"
    RETURNS = "RETURNS"
#endregion

class NeoGraphBuilder:
    def __init__(self, uri, user, password):
        """Initialize the graph builder with Neo4j connection details."""
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print("Successfully connected to Neo4j.")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()
            print("Neo4j connection closed.")

    def clear_graph(self):
        """Deletes all nodes and relationships in the graph."""
        if not self.driver: return
        print("Clearing the graph...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("Graph cleared.")

    ### --- CHANGE --- ###
    # This single method replaces all the repetitive create_*_node methods.
    # It uses a MERGE query which is idempotent: it creates the node if it doesn't exist
    # or matches it if it does. Then, it updates the properties. This is more efficient
    # and cleaner than the original check-then-create/update logic.
    def _create_or_update_node(self, session, node_obj: GraphNode):
        """
        Creates a node if it doesn't exist or updates it if it does.
        Uses the node's 'name' and 'type' as the unique key.
        Returns the internal Neo4j node ID.
        """
        label = node_obj.type
        properties = asdict(node_obj)
        
        # Using MERGE is the idiomatic way to create or find a node.
        # ON CREATE sets initial properties, ON MATCH updates them.
        query = (
            f"MERGE (n:{label} {{name: $properties.name, type: $properties.type}}) "
            "ON CREATE SET n = $properties "
            "ON MATCH SET n += $properties " # '+=' updates existing/adds new properties
            "RETURN id(n) AS node_id"
        )
        
        result = session.run(query, properties=properties)
        return result.single()["node_id"]

    def create_relationship(self, from_id, to_id, relationship: RelationshipType):
        """Creates a relationship between two nodes, preventing duplicates."""
        if not self.driver: return
        with self.driver.session() as session:
            # Using MERGE on relationships prevents creating duplicates.
            query = (
                f"MATCH (a) WHERE id(a) = $from_id "
                f"MATCH (b) WHERE id(b) = $to_id "
                f"MERGE (a)-[r:{relationship.value}]->(b) "
                "RETURN r"
            )
            session.run(query, from_id=from_id, to_id=to_id)
            
    def run_build_process(self, model_files: List[str]):
        if not self.driver:
            print("Cannot run build process, no database connection.")
            return

        with self.driver.session() as session:
            for file_path in model_files:
                print(f"Processing {file_path}...")
                with open(file_path) as f:
                    model_dict = json.load(f)

                # --- Repository Node ---
                repo_name = model_dict["Name"].lower()
                repo_node = RepoNode(name=repo_name)
                repo_id = self._create_or_update_node(session, repo_node)

                # --- Dependent Repositories ---
                for item in model_dict.get("DependentRepositories", []):
                    dep_repo_node = RepoNode(name=item.lower())
                    dep_repo_id = self._create_or_update_node(session, dep_repo_node)
                    self.create_relationship(repo_id, dep_repo_id, RelationshipType.DEPENDS_ON)
                
                # --- Controllers ---
                for item in model_dict.get("Controllers", []):
                    # Clean up controller name and type
                    name = item["Name"].replace('"', '')
                    ctrl_node = ControllerNode(name=name)
                    ctrl_id = self._create_or_update_node(session, ctrl_node)
                    self.create_relationship(repo_id, ctrl_id, RelationshipType.HAS_ROUTES)

                # --- Class Details ---
                for class_item in model_dict.get("ClassDetails", []):
                    class_node = ClassNode(
                        name=class_item["ClassName"],
                        file_path=class_item["FilePath"],
                        source=class_item["ClassSourceCode"],
                        ds=bool(class_item.get("Methods"))
                    )
                    class_id = self._create_or_update_node(session, class_node)
                    self.create_relationship(repo_id, class_id, RelationshipType.HAS_CLASSES)
                    
                    # Stored Procedures
                    for sp in class_item.get("StoredProcedure", []):
                        ### --- CHANGE --- ###
                        # Simplified the cleaning logic.
                        cleaned_name = sp.strip('[]"\' ').split('.')[-1]
                        sp_node = StoredProcedureNode(name=cleaned_name)
                        sp_id = self._create_or_update_node(session, sp_node)
                        self.create_relationship(class_id, sp_id, RelationshipType.CALLS_SP)

                    # Methods within the class
                    for method_item in class_item.get("Methods", []):
                        method_node = MethodNode(
                            name=method_item["MethodName"],
                            source=method_item["MethodSourceCode"],
                            return_type=method_item.get("MethodReturnType", "void")
                        )
                        method_id = self._create_or_update_node(session, method_node)
                        self.create_relationship(class_id, method_id, RelationshipType.HAS_METHOD)


def main():
    """Main execution function."""
    if not os.path.exists(SEMANTIC_MODEL_DIR):
        print(f"Error: Directory '{SEMANTIC_MODEL_DIR}' not found.")
        print("Please create it and place your JSON AST files inside.")
        return

    files = [os.path.join(SEMANTIC_MODEL_DIR, f) for f in os.listdir(SEMANTIC_MODEL_DIR) if f.endswith('.json')]
    if not files:
        print(f"No JSON files found in '{SEMANTIC_MODEL_DIR}'.")
        return

    builder = NeoGraphBuilder(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
    
    # Optional: Clear the graph before building. Use with caution.
    user_input = input("Do you want to clear the entire graph before building? (yes/no): ")
    if user_input.lower() == 'yes':
        builder.clear_graph()

    builder.run_build_process(files)
    builder.close()


if __name__ == "__main__":
    main()