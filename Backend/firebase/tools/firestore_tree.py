# tools/firestore_tree.py
# Lists collections / sample docs / subcollections so you can see the layout.
# Uses small limits to avoid cost/noise.

import firebase_admin
from firebase_admin import firestore

TOP_LEVEL_SAMPLE_DOCS = 5
SUBCOL_SAMPLE_DOCS = 3

def ensure_app():
    try:
        firebase_admin.get_app()
    except ValueError:
        # Relies on GOOGLE_APPLICATION_CREDENTIALS or default application creds
        firebase_admin.initialize_app()

def print_tree():
    ensure_app()
    db = firestore.client()

    print("=== Top-level collections ===")
    for col_ref in db.collections():
        print(f"\n/{col_ref.id}")
        # sample a few docs per collection
        docs = col_ref.limit(TOP_LEVEL_SAMPLE_DOCS).stream()
        for d in docs:
            print(f"  ├─ {d.id}")
            # list subcollections under this doc
            for sub in d.reference.collections():
                print(f"  │  └─ {sub.id}/ …")
                # sample a few sub-docs
                for sd in sub.limit(SUBCOL_SAMPLE_DOCS).stream():
                    print(f"  │     ├─ {sd.id}")
                # (don’t recurse infinitely; this already shows you the shape)

if __name__ == "__main__":
    print_tree()
