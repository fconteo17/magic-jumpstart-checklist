# Magic: The Gathering Jumpstart Checklist Generator

This tool generates printable **Checklist Cards** for Magic: The Gathering Jumpstart packs. It takes lists of cards and creates a PDF with standard-sized cards (62mm x 87mm), featuring graphical mana symbols, automatic grouping, and dynamic layout.

## Features

*   **Standard Card Size**: Generates cards sized 62mm x 87mm, perfect for sleeving with your Jumpstart packs.
*   **Automatic Grouping**: Cards are automatically sorted and grouped by type (Creatures, Planeswalkers, Spells, Artifacts, Enchantments, Lands).
*   **Graphical Mana Symbols**: Fetches official mana symbols from Scryfall and renders them right-aligned on the card.
*   **Quantity Support**: Handles quantities in input lists (e.g., `3x Mountain` or `7 Island`).
*   **Dynamic Font Sizing**: Automatically scales the text size to ensure the entire list fits on a single card, eliminating the need for pagination.
*   **Smart Parsing**:
    *   **Bracketed IDs**: Ignores bracketed IDs often found in export formats (e.g., `6 Plains [2t8d3...]` -> `6 Plains`).
    *   **Custom Variants**: Automatically recognizes custom names for basic lands (e.g., `Plains Appa` -> `Plains`).
*   **Caching**: Caches card data and symbol images locally to speed up subsequent runs and reduce API calls.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/fconteo17/magic-jumpstart.git
    cd magic-jumpstart
    ```

2.  **Install dependencies**:
    This project uses [uv](https://github.com/astral-sh/uv) for fast dependency management.
    ```bash
    # Install uv
    pip install uv

    # Create a virtual environment with required dependencies
    uv sync

    # Activate the virtual environment
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    # source .venv/bin/activate
    ```

## Usage

1.  **Prepare your lists**:
    Create text files (`.txt`) for each Jumpstart pack and place them in the `files/` directory.
    
    **Example `files/Pirates.txt`**:
    ```text
    Corsair Captain
    3x Mountain
    7 Island
    ```

2.  **Run the script**:
    ```bash
    python main.py
    ```

3.  **Get your PDF**:
    The script will generate `checklist_cards.pdf` in the root directory. Open it, print it (ensure "Actual Size" or 100% scale is selected in your printer settings), and cut out the cards.

## Configuration

*   **Card Size**: Defaults to 62mm x 87mm. You can adjust `CARD_WIDTH_MM` and `CARD_HEIGHT_MM` in `main.py` if needed.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
