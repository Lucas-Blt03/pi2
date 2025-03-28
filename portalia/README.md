# Portalia - Salary Calculator

This application provides a salary calculator tool that uses an Excel XLSM template with macros to generate accurate salary calculations based on various parameters.

## Project Structure

The project consists of two main components:

1. **Backend (FastAPI)**: Handles the calculation logic using the Excel XLSM template
2. **Frontend (Angular)**: Provides a user-friendly interface for the calculator

## Prerequisites

- Python 3.7+ with pip
- Node.js (v14+) and npm
- Microsoft Excel (required for xlwings to function properly)
- On Windows, make sure Excel is configured to allow running macros
- On macOS, you may need to install an additional Excel add-in for xlwings

## Setup Instructions

### Backend Setup

1. Create a virtual environment and activate it:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

3. Ensure you have the Excel XLSM file (`PORTALIA MC2 CONSULTANTS 2024 V0324 Copie.xlsm`) in the root directory of the project.

4. For xlwings to work properly with macros:
   - On Windows: Make sure Excel is configured to allow macros (set macro security to "Enable all macros")
   - On macOS: You may need to run `xlwings addin install` to install the Excel add-in

5. Start the FastAPI server:

```bash
uvicorn main:app --reload --log-level info
```

The backend API will be available at `http://127.0.0.1:8000`

### Frontend Setup

1. Navigate to the Angular project directory:

```bash
cd portalia
```

2. Install the required npm packages:

```bash
npm install
```

3. Start the Angular development server:

```bash
npm start
```

The frontend application will be available at `http://localhost:4200`

## Usage

1. Open your browser and navigate to `http://localhost:4200`
2. Fill in the calculator form with the required information:
   - Taux Journalier (€)
   - Nombre de Jours Travaillés
   - Type de Contrat (CDI/CDD)
   - Frais de Fonctionnement (%)
   - Ticket Restaurant (checkbox)
   - Mutuelle (checkbox)
   - Code Commune
3. Click "Calculer" to get your results

## Troubleshooting

If you encounter any issues with Excel automation:

1. **Excel Not Found**: Make sure Excel is installed and properly configured
2. **Macro Security**: Ensure Excel is configured to allow macros
3. **Excel Process Not Closing**: If Excel processes remain open after API calls, you may need to manually close them
4. **Cell References**: If calculations seem incorrect, check the logs to verify the cell references match your XLSM file's structure

## API Endpoints

- `GET /`: Welcome message
- `GET /convert`: Main conversion endpoint that uses Excel XLSM integration
- `GET /old_convert`: Legacy endpoint for simple calculations without Excel

## Notes

- The Excel XLSM file must be properly formatted with calculation sheets and templates
- If the XLSM file structure changes, you may need to adjust cell references in main.py
- Check the server logs for detailed information about Excel processing
- For production deployment, consider using a more robust Excel automation solution