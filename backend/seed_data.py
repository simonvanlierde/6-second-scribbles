"""
Seed script to load card deck data into the database

This script converts the TypeScript card deck data into database records.
Run this after setting up the database:
    python seed_data.py
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import async_session_maker, init_db
from db_models import Category, Card


# Card deck data (converted from TypeScript)
# Format: {"category": "Name", "items": [...], "language": "en"}
CARD_DECKS = {
    "easy": [
        {"category": "Animals", "items": ["cat", "dog", "fish", "bird", "rabbit", "cow", "duck", "sheep", "pig", "horse"], "language": "en"},
        {"category": "Fruits", "items": ["apple", "banana", "grapes", "pear", "pineapple", "watermelon", "kiwi", "cherry", "strawberry", "blueberry"], "language": "en"},
        {"category": "Vehicles", "items": ["car", "bus", "bicycle", "boat", "train", "truck", "motorcycle", "plane", "helicopter", "submarine"], "language": "en"},
        {"category": "Clothes", "items": ["shirt", "trousers", "dress", "skirt", "hat", "shoes", "socks", "scarf", "gloves", "coat"], "language": "en"},
        {"category": "Toys", "items": ["ball", "doll", "teddy bear", "kite", "yo-yo", "robot", "puzzle", "rubix cube", "frisbee", "jack in the box"], "language": "en"},
        {"category": "Food", "items": ["pizza", "burger", "hotdog", "sandwich", "cake", "cookie", "ice cream", "fries", "egg", "bread"], "language": "en"},
        {"category": "Nature", "items": ["tree", "flower", "leaf", "mountain", "river", "cloud", "sun", "moon", "star", "rain"], "language": "en"},
        {"category": "Household", "items": ["chair", "table", "bed", "lamp", "clock", "door", "window", "cup", "plate", "spoon"], "language": "en"},
        {"category": "Sports", "items": ["football", "basketball", "tennis", "baseball", "golf", "skateboard", "skiing", "swimming", "bowling", "boxing"], "language": "en"},
        {"category": "Jobs", "items": ["chef", "firefighter", "police officer", "doctor", "nurse", "teacher", "artist", "farmer", "pilot", "builder"], "language": "en"},
        {"category": "Musical Instruments", "items": ["drum", "guitar", "piano", "trumpet", "violin", "flute", "harmonica", "tambourine", "triangle", "maracas"], "language": "en"},
        {"category": "Sea Creatures", "items": ["crab", "starfish", "jellyfish", "shrimp", "clam", "seal", "seahorse", "lobster", "turtle", "dolphin"], "language": "en"},
        {"category": "Buildings", "items": ["house", "tent", "castle", "igloo", "lighthouse", "windmill", "church", "store", "school", "fire station"], "language": "en"},
        {"category": "Actions", "items": ["running", "jumping", "sitting", "sleeping", "eating", "reading", "waving", "swimming", "dancing", "singing"], "language": "en"},
        {"category": "Weather", "items": ["rain", "snow", "wind", "sun", "cloud", "storm", "fog", "hail", "lightning", "rainbow"], "language": "en"},
        {"category": "Insects", "items": ["ant", "bee", "butterfly", "beetle", "ladybug", "mosquito", "dragonfly", "spider", "worm", "caterpillar"], "language": "en"},
        {"category": "Emotions", "items": ["happy", "sad", "angry", "excited", "bored", "scared", "sleepy", "surprised", "confused", "laughing"], "language": "en"},
        {"category": "School", "items": ["book", "pencil", "eraser", "ruler", "chalkboard", "desk", "backpack", "notebook", "glue", "scissors"], "language": "en"},
        {"category": "Body Parts", "items": ["hand", "foot", "eye", "ear", "mouth", "nose", "leg", "arm", "hair", "teeth"], "language": "en"},
        {"category": "Candy", "items": ["lollipop", "chocolate", "candy cane", "gum", "gummy bear", "jellybean", "marshmallow", "toffee", "caramel", "mint"], "language": "en"},
        {"category": "Pets", "items": ["dog", "cat", "rabbit", "hamster", "goldfish", "turtle", "parrot", "mouse", "frog", "snake"], "language": "en"},
        {"category": "Fantasy", "items": ["unicorn", "dragon", "fairy", "elf", "witch", "wizard", "goblin", "troll", "giant", "mermaid"], "language": "en"},
        {"category": "Transport Parts", "items": ["wheel", "engine", "steering wheel", "seatbelt", "mirror", "door", "trunk", "window", "pedal", "horn"], "language": "en"},
        {"category": "Tools", "items": ["hammer", "screwdriver", "saw", "wrench", "drill", "pliers", "tape measure", "nail", "axe", "toolbox"], "language": "en"},
        {"category": "At the Park", "items": ["slide", "swing", "tree", "bench", "ball", "kite", "duck pond", "fountain", "picnic basket", "flower"], "language": "en"},
        {"category": "Things that are Round", "items": ["ball", "clock", "sun", "moon", "orange", "button", "coin", "pizza", "wheel", "cookie"], "language": "en"},
        {"category": "Vegetables", "items": ["carrot", "broccoli", "tomato", "potato", "onion", "corn", "lettuce", "bell pepper", "cucumber", "mushroom"], "language": "en"},
        {"category": "Places", "items": ["park", "beach", "library", "store", "home", "hospital", "restaurant", "airport", "zoo", "museum"], "language": "en"},
        {"category": "Kitchen Items", "items": ["fork", "knife", "spoon", "plate", "bowl", "pan", "pot", "cutting board", "spatula", "whisk"], "language": "en"},
        {"category": "In the Sky", "items": ["sun", "moon", "star", "cloud", "airplane", "bird", "kite", "rainbow", "balloon", "satellite"], "language": "en"},
        {"category": "Bathroom Items", "items": ["soap", "towel", "toothbrush", "toothpaste", "toilet", "sink", "bathtub", "shower", "shampoo", "mirror"], "language": "en"},

        # Spanish categories (Español)
        {"category": "Animales", "items": ["gato", "perro", "pez", "pájaro", "conejo", "vaca", "pato", "oveja", "cerdo", "caballo"], "language": "es"},
        {"category": "Frutas", "items": ["manzana", "plátano", "uvas", "pera", "piña", "sandía", "kiwi", "cereza", "fresa", "arándano"], "language": "es"},
        {"category": "Vehículos", "items": ["coche", "autobús", "bicicleta", "barco", "tren", "camión", "motocicleta", "avión", "helicóptero", "submarino"], "language": "es"},
        {"category": "Ropa", "items": ["camisa", "pantalones", "vestido", "falda", "sombrero", "zapatos", "calcetines", "bufanda", "guantes", "abrigo"], "language": "es"},
        {"category": "Comida", "items": ["pizza", "hamburguesa", "perrito caliente", "bocadillo", "pastel", "galleta", "helado", "patatas fritas", "huevo", "pan"], "language": "es"},
        {"category": "Naturaleza", "items": ["árbol", "flor", "hoja", "montaña", "río", "nube", "sol", "luna", "estrella", "lluvia"], "language": "es"},
        {"category": "Deportes", "items": ["fútbol", "baloncesto", "tenis", "béisbol", "golf", "monopatín", "esquí", "natación", "bolos", "boxeo"], "language": "es"},
        {"category": "Emociones", "items": ["feliz", "triste", "enojado", "emocionado", "aburrido", "asustado", "somnoliento", "sorprendido", "confundido", "riendo"], "language": "es"},

        # French categories (Français)
        {"category": "Animaux", "items": ["chat", "chien", "poisson", "oiseau", "lapin", "vache", "canard", "mouton", "cochon", "cheval"], "language": "fr"},
        {"category": "Fruits", "items": ["pomme", "banane", "raisins", "poire", "ananas", "pastèque", "kiwi", "cerise", "fraise", "myrtille"], "language": "fr"},
        {"category": "Véhicules", "items": ["voiture", "bus", "vélo", "bateau", "train", "camion", "moto", "avion", "hélicoptère", "sous-marin"], "language": "fr"},
        {"category": "Vêtements", "items": ["chemise", "pantalon", "robe", "jupe", "chapeau", "chaussures", "chaussettes", "écharpe", "gants", "manteau"], "language": "fr"},
        {"category": "Nourriture", "items": ["pizza", "hamburger", "hot-dog", "sandwich", "gâteau", "biscuit", "glace", "frites", "œuf", "pain"], "language": "fr"},
        {"category": "Nature", "items": ["arbre", "fleur", "feuille", "montagne", "rivière", "nuage", "soleil", "lune", "étoile", "pluie"], "language": "fr"},
        {"category": "Sports", "items": ["football", "basketball", "tennis", "baseball", "golf", "skateboard", "ski", "natation", "bowling", "boxe"], "language": "fr"},
        {"category": "Émotions", "items": ["heureux", "triste", "en colère", "excité", "ennuyé", "effrayé", "endormi", "surpris", "confus", "riant"], "language": "fr"},
    ],
    "medium": [
        {"category": "Musical Instruments", "items": ["Guitar", "Piano", "Drums", "Violin", "Trumpet", "Flute", "Saxophone", "Harp", "Banjo", "Clarinet"], "language": "en"},
        {"category": "Sports Equipment", "items": ["Baseball", "Basketball", "Soccer Ball", "Tennis Racket", "Golf Club", "Hockey Stick", "Volleyball", "Skateboard", "Bicycle", "Helmet"], "language": "en"},
        {"category": "Kitchen Items", "items": ["Fork", "Knife", "Spoon", "Pot", "Pan", "Spatula", "Whisk", "Cutting Board", "Mixing Bowl", "Colander"], "language": "en"},
        {"category": "Weather Phenomena", "items": ["Rain", "Snow", "Thunder", "Lightning", "Rainbow", "Clouds", "Wind", "Fog", "Hail", "Tornado"], "language": "en"},

        # Spanish medium categories
        {"category": "Instrumentos Musicales", "items": ["Guitarra", "Piano", "Batería", "Violín", "Trompeta", "Flauta", "Saxofón", "Arpa", "Banjo", "Clarinete"], "language": "es"},
        {"category": "Equipo Deportivo", "items": ["Béisbol", "Baloncesto", "Balón de Fútbol", "Raqueta de Tenis", "Palo de Golf", "Palo de Hockey", "Voleibol", "Monopatín", "Bicicleta", "Casco"], "language": "es"},

        # French medium categories
        {"category": "Instruments de Musique", "items": ["Guitare", "Piano", "Batterie", "Violon", "Trompette", "Flûte", "Saxophone", "Harpe", "Banjo", "Clarinette"], "language": "fr"},
        {"category": "Équipement Sportif", "items": ["Baseball", "Basketball", "Ballon de Foot", "Raquette de Tennis", "Club de Golf", "Crosse de Hockey", "Volleyball", "Skateboard", "Vélo", "Casque"], "language": "fr"},
    ],
    "hard": [
        {"category": "Abstract Concepts", "items": ["Love", "Freedom", "Justice", "Peace", "Anger", "Joy", "Fear", "Hope", "Trust", "Wisdom"], "language": "en"},
        {"category": "Historical Figures", "items": ["Einstein", "Napoleon", "Shakespeare", "Cleopatra", "Gandhi", "Caesar", "Mozart", "Picasso", "Edison", "Columbus"], "language": "en"},
        {"category": "Scientific Terms", "items": ["Atom", "Molecule", "Gravity", "Evolution", "Photosynthesis", "Electricity", "Magnet", "Velocity", "Energy", "Friction"], "language": "en"},
        {"category": "Architecture", "items": ["Arch", "Column", "Dome", "Pyramid", "Bridge", "Tower", "Skyscraper", "Cathedral", "Lighthouse", "Aqueduct"], "language": "en"},
    ]
}


async def seed_database():
    """Seed the database with card deck data"""
    print("🌱 Starting database seed...")

    # Initialize database tables
    await init_db()
    print("✅ Database tables initialized")

    async with async_session_maker() as session:
        try:
            # Check if data already exists
            from sqlalchemy import select
            result = await session.execute(select(Category))
            existing = result.scalars().all()

            if existing:
                print("⚠️  Database already contains data. Skipping seed.")
                print(f"   Found {len(existing)} categories")
                return

            # Seed data for each difficulty level
            total_categories = 0
            total_items = 0

            for difficulty, categories in CARD_DECKS.items():
                print(f"\n📦 Seeding {difficulty} categories...")

                for cat_data in categories:
                    # Create category
                    category = Category(
                        name=cat_data["category"],
                        difficulty=difficulty,
                        language=cat_data.get("language", "en"),  # Default to 'en' if not specified
                        description=f"{difficulty.capitalize()} difficulty category"
                    )
                    session.add(category)
                    await session.flush()  # Flush to get the ID

                    # Create cards for this category
                    for item in cat_data["items"]:
                        card = Card(
                            category_id=category.id,
                            item=item,
                            alternatives=[]  # Can add alternatives later
                        )
                        session.add(card)

                    total_categories += 1
                    total_items += len(cat_data["items"])

                    print(f"   ✓ {cat_data['category']} ({len(cat_data['items'])} items)")

            # Commit all changes
            await session.commit()

            print(f"\n✅ Seed complete!")
            print(f"   📊 {total_categories} categories created")
            print(f"   📝 {total_items} items added")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise


async def clear_database():
    """Clear all data from the database (use with caution!)"""
    print("⚠️  Clearing database...")

    async with async_session_maker() as session:
        try:
            # Delete all cards (will cascade)
            from sqlalchemy import delete
            await session.execute(delete(Category))
            await session.commit()
            print("✅ Database cleared")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error clearing database: {e}")
            raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        asyncio.run(clear_database())
    else:
        asyncio.run(seed_database())
