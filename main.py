from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import shutil
from typing import Optional
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# Path to the Excel template - exact name as provided
EXCEL_TEMPLATE_PATH = "PORTALIA MC2 CONSULTANTS 2024 V0324.xlsm"

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur FastAPI"}

def str_to_bool(value: str) -> bool:
    """Convert string to boolean, handling various formats."""
    if not value:
        return False
    return value.lower() in ('true', 't', 'yes', 'y', '1')

@app.get("/get-excel-info")
def get_excel_info():
    """Endpoint to check Excel file information"""
    info = {
        "excel_file": EXCEL_TEMPLATE_PATH,
        "exists": os.path.exists(EXCEL_TEMPLATE_PATH),
        "file_size": os.path.getsize(EXCEL_TEMPLATE_PATH) if os.path.exists(EXCEL_TEMPLATE_PATH) else 0,
        "current_directory": os.getcwd(),
        "python_version": sys.version,
        "available_files": [f for f in os.listdir('.') if f.endswith('.xlsm') or f.endswith('.xlsx')]
    }
    return info

@app.get("/convert")
async def convert(
    tjm: Optional[float] = Query(None),
    jours_travailles: Optional[int] = Query(None),
    contract_type: Optional[str] = Query(None),
    frais_fonctionnement: Optional[float] = Query(None),
    ticket_restaurant: Optional[str] = Query(None),
    mutuelle: Optional[str] = Query(None),
    code_commune: Optional[str] = Query(None),
    valeur_j9: Optional[str] = Query(None)
):
    # Log the received parameters
    logger.info(f"Received parameters: tjm={tjm}, jours_travailles={jours_travailles}, " +
                f"contract_type={contract_type}, frais_fonctionnement={frais_fonctionnement}, " +
                f"ticket_restaurant={ticket_restaurant}, mutuelle={mutuelle}, code_commune={code_commune}, " +
                f"valeur_j9={valeur_j9}")
    
    # Convert string boolean parameters to actual booleans
    ticket_restaurant_bool = str_to_bool(ticket_restaurant) if ticket_restaurant is not None else False
    mutuelle_bool = str_to_bool(mutuelle) if mutuelle is not None else False
    
    # Check if we have the required parameters
    if tjm is None or jours_travailles is None:
        error_msg = "TJM and jours_travailles are required"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Check if Excel file exists
    if not os.path.exists(EXCEL_TEMPLATE_PATH):
        error_msg = f"Excel template file not found: {EXCEL_TEMPLATE_PATH}"
        logger.error(error_msg)
        files_in_dir = ", ".join([f for f in os.listdir('.') if f.endswith('.xlsm') or f.endswith('.xlsx')])
        error_msg += f". Available Excel files: {files_in_dir}"
        raise HTTPException(status_code=500, detail=error_msg)
    
    # Import xlwings here to avoid startup errors if Excel is not available
    try:
        import xlwings as xw
    except ImportError:
        error_msg = "xlwings module not installed. Please install it with: pip install xlwings"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    try:
        logger.info(f"Starting Excel processing with TJM={tjm}, jours={jours_travailles}")
        
        # Create a temporary copy of the template
        temp_dir = tempfile.mkdtemp()
        temp_excel_path = os.path.join(temp_dir, "temp_calculation.xlsm")
        shutil.copy2(EXCEL_TEMPLATE_PATH, temp_excel_path)
        logger.info(f"Copied template to {temp_excel_path}")
        
        # Open the Excel file with xlwings - without using App.config
        app_excel = xw.App(visible=False)
        app_excel.display_alerts = False
        app_excel.screen_updating = False
        
        # Try to open with specified path
        try:
            logger.info(f"Attempting to open Excel file: {temp_excel_path}")
            wb = app_excel.books.open(temp_excel_path)
            logger.info("Excel file opened successfully")
        except Exception as e2:
                logger.error(f"Error opening Excel with absolute path: {e2}")
                raise HTTPException(status_code=500, 
                                   detail=f"Could not open Excel file: {str(e)}. Tried absolute path: {str(e2)}")

        try:
            # Get all sheet names for debugging
            sheet_names = [sheet.name for sheet in wb.sheets]
            logger.info(f"Excel sheets: {sheet_names}")
            
            # Look for the calculation sheet - try multiple possible names
            calculation_sheet_name = "1. Calcul Avec prov"
            
            # Access the calculation sheet
            ws = wb.sheets[calculation_sheet_name]
            
            # Fill in the data
            logger.info("Setting values in Excel...")
            
            ws.range("J4").value = tjm
            logger.info(f"Set TJM to {tjm} in cell J4")
            
            ws.range("J5").value = jours_travailles
            logger.info(f"Set jours travaillés to {jours_travailles} in cell J5")
            
            # Handle contract type
            if contract_type == "CDI":
                ws.range("J8").value = 0.02
                ws.range("J9").value = 0.1
                ws.range("J10").value = 0
                logger.info(f"Set contract type to CDI")
            elif contract_type == "CDD":
                ws.range("J8").value = 0
                ws.range("J9").value = 0
                ws.range("J10").value = 0.1
                logger.info("Set contract type to CDD")
            
            # Handle frais de fonctionnement
            if frais_fonctionnement is not None:
                ws.range("J12").value = frais_fonctionnement*100
                logger.info(f"Set frais de fonctionnement to {frais_fonctionnement*100} in cell J12")
            
            # Handle ticket restaurant
            if ticket_restaurant_bool:
                ws.range("J21").value = jours_travailles * 11
                logger.info("Enabled ticket restaurant in cell J21")
            else:
                ws.range("J21").value = 0
                logger.info("Disabled ticket restaurant in cell J21")
            
            # Handle mutuelle
            if mutuelle_bool:
                ws.range("J17").value = "Oui"
                logger.info("Set mutuelle to 'Oui' in cell J17")
            else:
                ws.range("J17").value = "Non"
                logger.info("Set mutuelle to 'Non' in cell J17")
            
            # Handle code commune
            if code_commune:
                # Vérifier d'abord si la feuille tauxTransport existe
                transport_sheet_name = "tauxTransport.20240102"
                
                if transport_sheet_name:
                    transport_sheet = wb.sheets[transport_sheet_name]
                    
                    # Récupérer tous les codes commune de la colonne A
                    try:
                        # Obtenir la plage utilisée
                        used_range = transport_sheet.used_range
                        last_row = used_range.last_cell.row
                        codes_list = []
                        
                        # Logging pour débogage
                        logger.info(f"Analyse de la feuille {transport_sheet_name} jusqu'à la ligne {last_row}")
                        
                        # Lire tous les codes communes et les normaliser pour la comparaison
                        #for row in range(2, last_row + 1): 
                        for row in range(2, 100): # Commencer à la ligne 2 pour éviter l'en-tête
                            cell_value = transport_sheet.range(f"A{row}").value
                            if cell_value is not None:
                                # Convertir en string et normaliser
                                normalized_code = str(cell_value).strip()
                                codes_list.append(normalized_code)
                        
                        # Normaliser le code fourni par l'utilisateur
                        normalized_user_code = str(code_commune).strip().lstrip('0')  # Enlever le zéro initial
                        logger.info(f"Code fourni par l'utilisateur (normalisé): '{normalized_user_code}'")
                        logger.info(f"Codes disponibles: {codes_list[:20]}...")  # Afficher les 20 premiers codes
                        
                        # Vérification avec affichage détaillé
                        if normalized_user_code in codes_list or str(normalized_user_code) in [str(code).split('.')[0] for code in codes_list]:
                            logger.info(f"Code commune '{normalized_user_code}' TROUVÉ dans la liste")
                            ws.range("J25").value = code_commune
                            logger.info(f"Code commune appliqué dans cell J25")
                        else:
                            logger.warning(f"Code commune '{normalized_user_code}' NON TROUVÉ dans la liste")
                            
                            # Recherche approximative pour aider au débogage
                            close_matches = [code for code in codes_list if normalized_user_code in code or code in normalized_user_code]
                            if close_matches:
                                logger.info(f"Correspondances proches trouvées: {close_matches}")
                            
                            # Lève une exception avec un message personnalisé
                            from fastapi.responses import JSONResponse
                            return JSONResponse(
                                status_code=400,
                                content={"message": "Le code Commune n'est pas dans la base de données"}
                            )
                    except Exception as e:
                        logger.error(f"Erreur lors de la vérification du code commune: {e}")
                        # En cas d'erreur technique, on continue sans appliquer le code
                        raise HTTPException(status_code=500, 
                                        detail="Erreur lors de la vérification du code commune")
                else:
                    logger.warning("Feuille des taux de transport non trouvée, impossible de vérifier le code commune")
                    # Si on ne peut pas vérifier, on considère que c'est une erreur
                    raise HTTPException(status_code=500, 
                                    detail="Impossible de vérifier le code commune (feuille non trouvée)")
   
            # Force calculation
            logger.info("Forcing Excel calculation...")
            wb.app.calculate()
            
            # Try to run the macro if it exists
            try:
                logger.info("Attempting to run macro...")
                # First check if the TJM macro exists
                wb.macro("TJM")()
                logger.info("Successfully ran TJM macro")
            except Exception as e:
                logger.warning(f"Error running TJM macro: {e}")
                # Try other common macro names
                for macro_name in ["UpdateTemplate", "MAJ", "Calculate"]:
                    try:
                        wb.macro(macro_name)()
                        logger.info(f"Successfully ran {macro_name} macro")
                        break
                    except Exception as e2:
                        logger.warning(f"Error running {macro_name} macro: {e2}")
            
            # Look for template sheet for results
            template_sheet_name = None
            possible_template_sheets = ["Template", "3. Template", "Résultats"]
            
            for sheet_name in possible_template_sheets:
                if sheet_name in sheet_names:
                    template_sheet_name = sheet_name
                    logger.info(f"Found template sheet: {template_sheet_name}")
                    break
            
            if not template_sheet_name:
                # Try to find by content
                for sheet_name in sheet_names:
                    try:
                        if "template" in sheet_name.lower() or "résultat" in sheet_name.lower():
                            template_sheet_name = sheet_name
                            logger.info(f"Found template sheet via name match: {template_sheet_name}")
                            break
                    except Exception:
                        pass
            
            if not template_sheet_name:
                # If still not found, we'll use the calculation sheet to try to get results
                template_sheet_name = calculation_sheet_name
                logger.warning(f"Using calculation sheet for results: {template_sheet_name}")
            
            template_sheet = wb.sheets[template_sheet_name]
            
            # Debug: print values in key cells
            debug_cells = {
                
                "brut_mensuel" : template_sheet.range("E23").value,
                "net_mensuel" : template_sheet.range("E26").value,
                "frais_gestion" : template_sheet.range("E8").value,
                "ticket_contribution" : template_sheet.range("E18").value if ticket_restaurant_bool else 0,
                "mutuelle_contribution": template_sheet.range("E14").value if mutuelle_bool else 0
                }
            logger.info(f"Debug cell values: {debug_cells}")
            
            # Try to get results from different locations
            # First try the template sheet cells mentioned in your code
            brut_mensuel = template_sheet.range("E23").value
            net_mensuel = template_sheet.range("E26").value
            frais_gestion = template_sheet.range("E8").value
            ticket_contribution = template_sheet.range("E18").value if ticket_restaurant_bool else 0
            mutuelle_contribution = template_sheet.range("E14").value if mutuelle_bool else 0
            
            # If those are not available, try the cells from calculation sheet
            if brut_mensuel is None:
                brut_mensuel = ws.range("B5").value
                logger.info(f"Using B5 for brut_mensuel: {brut_mensuel}")
            
            if net_mensuel is None:
                net_mensuel = ws.range("B9").value
                logger.info(f"Using B9 for net_mensuel: {net_mensuel}")
            
            if frais_gestion is None:
                frais_gestion = ws.range("J11").value
                logger.info(f"Using J11 for frais_gestion: {frais_gestion}")
            
            # Construct the result
            result = {
                "tjm": tjm,
                "brut_mensuel": brut_mensuel,
                "net_mensuel": net_mensuel,
                "frais_gestion": frais_gestion,
                "autres_details": {
                    "ticket_restaurant_contribution": ticket_contribution,
                    "mutuelle_contribution": mutuelle_contribution,
                }
            }
            
            logger.info(f"Final result: {result}")
            return result
            
        finally:
            # Ensure proper cleanup
            try:
                logger.info("Cleaning up Excel resources...")
                wb.save()
                wb.close()
                app_excel.quit()
                shutil.rmtree(temp_dir)
                logger.info("Excel cleanup completed")
            except Exception as e:
                logger.error(f"Error during Excel cleanup: {e}")
    
    except Exception as e:
        error_msg = f"Excel processing error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# Fallback endpoint that returns dummy data
@app.get("/fallback-convert")
def fallback_convert(
    tjm: Optional[float] = Query(500),
    jours_travailles: Optional[int] = Query(18),
    contract_type: Optional[str] = Query("CDI"),
    ticket_restaurant: Optional[bool] = Query(False),
    mutuelle: Optional[bool] = Query(False)
):
    """Fallback endpoint that returns dummy data when Excel fails"""
    return {
        "tjm": tjm,
        "brut_mensuel": 7500.0,
        "net_mensuel": 5250.0,
        "frais_gestion": 750.0,
        "autres_details": {
            "ticket_restaurant_contribution": 198 if ticket_restaurant else 0,
            "mutuelle_contribution": 50 if mutuelle else 0,
        },
        "note": "This is fallback data. Excel automation failed."
    }