#!/usr/bin/env python3
"""
Neo4j ADL/IADL Knowledge Graph Seeder
Seeds the knowledge graph to align with clinical_assessment_data and Postgres, with IADL first.
"""

import os
import sys
from neo4j import GraphDatabase
from clinical_assessment_data import get_adl_questions, get_iadl_questions, get_all_questions

class Neo4jSeeder:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_database(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ Cleared existing data")

    def create_constraints(self):
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT question_code_unique IF NOT EXISTS FOR (q:Question) REQUIRE q.code IS UNIQUE",
                "CREATE CONSTRAINT answer_id_unique IF NOT EXISTS FOR (a:Answer) REQUIRE a.id IS UNIQUE",
                "CREATE CONSTRAINT domain_name_unique IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE"
            ]
            for c in constraints:
                session.run(c)
            print("✓ Created constraints")

    def create_domains_questions_answers(self):
        with self.driver.session() as session:
            # Domains from clinical data (IADL then ADL)
            domains = {}
            for question in get_iadl_questions() + get_adl_questions():
                dname = question['domain']
                dtype = question['assessment_type']
                if dname not in domains:
                    session.run(
                        """
                        CREATE (d:Domain {name: $name, type: $type})
                        """, name=dname, type=dtype
                    )
                    domains[dname] = dtype

            print(f"✓ Created {len(domains)} Domain nodes")

            # Questions & Answers (link domain, question, answer)
            for question in get_iadl_questions() + get_adl_questions():
                # Question node
                session.run(
                    """
                    MATCH (d:Domain {name: $domain})
                    CREATE (q:Question {
                        code: $code,
                        text: $text,
                        assessment_type: $assessment_type,
                        domain: $domain,
                        sequence: $sequence,
                        description: $description
                    })
                    CREATE (d)-[:HAS_QUESTION]->(q)
                    """,
                    code=question["code"],
                    text=question["text"],
                    assessment_type=question["assessment_type"],
                    domain=question["domain"],
                    sequence=question["sequence"],
                    description=question.get("description", "")
                )

                # Answer nodes
                for ans in question["answers"]:
                    session.run(
                        """
                        MATCH (q:Question {code: $question_code})
                        CREATE (a:Answer {
                            text: $text,
                            clinical_score: $clinical_score,
                            answer_order: $order
                        })
                        CREATE (q)-[:HAS_OPTION]->(a)
                        """,
                        question_code=question["code"],
                        text=ans["text"],
                        clinical_score=ans["clinical_score"],
                        order=ans["order"]
                    )
            print(f"✓ Created questions and answers, linked to domains")

    def create_sequential_flow(self):
        with self.driver.session() as session:
            # IADL sequence first
            questions = get_iadl_questions() + get_adl_questions()
            for i in range(len(questions) - 1):
                q_code = questions[i]["code"]
                next_code = questions[i+1]["code"]
                session.run(
                    """
                    MATCH (q1:Question {code: $q_code})
                    MATCH (q2:Question {code: $next_code})
                    CREATE (q1)-[:NEXT_QUESTION]->(q2)
                    """,
                    q_code=q_code, next_code=next_code
                )
            print("✓ Created sequential flow: IADL → ADL")

            # Add AssessmentFlow start/completion nodes and flow
            session.run("""
                CREATE (start:AssessmentFlow {
                    id: 'start',
                    type: 'introduction',
                    message: "Let's begin your daily living abilities assessment. Please answer the following questions."
                })
            """)
            session.run("""
                CREATE (end:AssessmentFlow {
                    id: 'completion',
                    type: 'completion',
                    message: "Thank you for completing the assessment."
                })
            """)
            first_code = questions[0]["code"]
            last_code = questions[-1]["code"]
            session.run(
                """
                MATCH (start:AssessmentFlow {id: 'start'})
                MATCH (first:Question {code: $first_code})
                CREATE (start)-[:LEADS_TO]->(first)
                """, first_code=first_code
            )
            session.run(
                """
                MATCH (last:Question {code: $last_code})
                MATCH (end:AssessmentFlow {id: 'completion'})
                CREATE (last)-[:LEADS_TO]->(end)
                """, last_code=last_code
            )
            print("✓ Created AssessmentFlow nodes and edges")

    def verify(self):
        with self.driver.session() as session:
            counts = {
                "domains": session.run("MATCH (d:Domain) RETURN count(d) as c").single()["c"],
                "questions": session.run("MATCH (q:Question) RETURN count(q) as c").single()["c"],
                "answers": session.run("MATCH (a:Answer) RETURN count(a) as c").single()["c"],
                "flows": session.run("MATCH (f:AssessmentFlow) RETURN count(f) as c").single()["c"],
                "seq_edges": session.run("MATCH ()-[r:NEXT_QUESTION]->() RETURN count(r) as c").single()["c"],
                "option_edges": session.run("MATCH ()-[r:HAS_OPTION]->() RETURN count(r) as c").single()["c"],
                "dom_edges": session.run("MATCH ()-[r:HAS_QUESTION]->() RETURN count(r) as c").single()["c"],
            }
            print("=== VERIFICATION ===")
            for k, v in counts.items():
                print(f"{k}: {v}")

def main():
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
    print("=== Knowledge Graph Seeder ===")
    try:
        seeder = Neo4jSeeder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        print("\n1. Clearing database...")
        seeder.clear_database()
        print("\n2. Creating constraints...")
        seeder.create_constraints()
        print("\n3. Creating domains, questions, answers...")
        seeder.create_domains_questions_answers()
        print("\n4. Creating sequential flow...")
        seeder.create_sequential_flow()
        print("\n5. Verifying...")
        seeder.verify()
        seeder.close()
        print("\n✅ Neo4j seeding complete and consistent with clinical/Postgres data!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
