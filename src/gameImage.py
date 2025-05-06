from pathlib import Path
from PIL.ImageTk import PhotoImage

class GameImage:
    def __init__(self):
        """
        Initializes a game image object that holds all of the images for the game.
        The images folder is assumed to live under the project root at 'static/images',
        alongside your 'src' folder.
        """
        # Locate this file (e.g. src/balance_board.py or wherever you put this)
        this_file = Path(__file__).resolve()
        src_dir    = this_file.parent           # e.g. .../your_project/src
        project_root = src_dir.parent           # e.g. .../your_project

        # static/images under the project root
        images_dir = project_root / "static" / "images"
        if not images_dir.is_dir():
            raise FileNotFoundError(f"Could not find images folder at {images_dir}")

        # Load all common image extensions
        self.game_images = {}
        for img_path in images_dir.iterdir():
            if img_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}:
                key = img_path.stem  # filename without extension
                # PhotoImage expects a string path
                self.game_images[key] = PhotoImage(file=str(img_path))

    def return_image(self, name) -> PhotoImage:
        """
        Returns the PhotoImage for the given key (filename without extension).
        Raises a KeyError if not found.
        """
        try:
            return self.game_images[name]
        except KeyError:
            available = ", ".join(self.game_images.keys())
            raise KeyError(f"No image named '{name}'. Available: {available}")