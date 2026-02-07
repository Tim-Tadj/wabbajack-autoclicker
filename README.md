- **Oh yeah, and it's probably against Nexus TOS.**

## Prerequisites
If you just want to run the application, download the installer from the Releases page.

If you want to build it from source:
1. Install [uv](https://docs.astral.sh/uv/).
   `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Clone this repository.
3. Run `uv sync` to install dependencies.

## Building

To create a Windows Installer (.msi):
```powershell
uv run cxfreeze bdist_msi
```
The installer will be located in the `dist/` folder.

To create a standalone executable folder:
```powershell
uv run cxfreeze build
```
The executable will be in `build/exe.win-amd64-3.12/`.

## Usage

1. Run Wabbajack and begin downloading your modlist.
2. Launch **Wabbajack Autoclicker** (from Start Menu or via `uv run "wabbajack autoclicker.py"`).
3. When the Nexus Mods download page appears, click **Capture Screenshot** in the app and select the "SLOW DOWNLOAD" button area.

!Example of the SLOW DOWNLOAD button

4. Select your network interface from the dropdown.
5. Click **Start**.
