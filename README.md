# Curator

**Curator** is a simple portfolio manager for visual arts and photography, built with Python, GTK 4, and Libadwaita.


## Description

Curator helps you organize and manage your portfolios efficiently. It provides a clean and modern interface for creating, editing, and exporting your artistic collections.

## Requirements

*   Python 3
*   GTK 4
*   Libadwaita
*   PyGObject

## Installation & Running

### From Source

1.  Ensure you have the required dependencies installed (including `libgtk-4-dev`, `libadwaita-1-dev`, `python3-gi`, etc.).
2.  Clone the repository.
3.  Compile the resources:
    ```bash
    glib-compile-resources curator.gresource.xml
    ```
4.  Run the application:
    ```bash
    ./curator.sh
    ```

### Flatpak

This application is designed to be built and run as a Flatpak.

1.  Install `flatpak` and `flatpak-builder`.
2.  Build and install:
    ```bash
    flatpak-builder --user --install build com.github.cadmiumcmyk.Curator.json
    ```
3.  Run:
    ```bash
    flatpak run com.github.cadmiumcmyk.Curator
    ```

## License

This project is licensed under the GPLv3 License. See the [LICENSE](LICENSE) file for details.
