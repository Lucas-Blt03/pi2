from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import shutil
from typing import Optional, Dict, List
import logging
import sys
import time

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

# Path to the Excel template - mise à jour pour 2025
EXCEL_TEMPLATE_PATH = "PORTALIA MC2 CONSULTANTS 2025 V012025.xlsm"

# Cache pour les codes communes pour éviter de relire le fichier Excel à chaque fois
COMMUNE_CODES_CACHE: Dict[str, List[str]] = {}

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

def is_commune_code_valid(code_commune: str, transport_sheet) -> bool:
    """
    Vérifier si le code commune est valide en utilisant un cache et une recherche optimisée.
    """
    # Format the cache key based on sheet name or other identifier
    cache_key = "transport_codes"
    
    # Check if communes are already cached
    if cache_key not in COMMUNE_CODES_CACHE:
        try:
            # This is the first time, load all codes at once and cache them
            logger.info("Loading commune codes into cache")
            start_time = time.time()
            
            # Get the used range
            used_range = transport_sheet.used_range
            last_row = used_range.last_cell.row
            
            # Read codes in chunks for better performance
            codes_list = []
            chunk_size = 100
            
            for start_row in range(2, last_row + 1, chunk_size):
                end_row = min(start_row + chunk_size - 1, last_row)
                cell_range = f"A{start_row}:A{end_row}"
                
                # Read the chunk of values
                chunk_values = transport_sheet.range(cell_range).value
                
                # Handle single value case
                if not isinstance(chunk_values, list):
                    chunk_values = [chunk_values]
                
                # Process the values from the chunk
                for value in chunk_values:
                    if value is not None:
                        normalized_code = str(value).strip()
                        codes_list.append(normalized_code)
            
            COMMUNE_CODES_CACHE[cache_key] = codes_list
            logger.info(f"Cached {len(codes_list)} commune codes in {time.time() - start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error loading commune codes into cache: {str(e)}")
            return False
    
    # Now check if the provided code is in the cached list
    normalized_user_code = str(code_commune).strip().lstrip('0')
    
    # Direct lookup first (faster)
    if normalized_user_code in COMMUNE_CODES_CACHE[cache_key]:
        return True
    
    # Check with split (for codes with decimal points)
    for code in COMMUNE_CODES_CACHE[cache_key]:
        if normalized_user_code == code.split('.')[0]:
            return True
    
    return False

@app.get("/convert")
async def convert(
    tjm: Optional[float] = Query(None),
    jours_travailles: Optional[int] = Query(None),
    contract_type: Optional[str] = Query(None),
    frais_fonctionnement: Optional[float] = Query(None),
    frais_gestion: Optional[float] = Query(None),
    provision_negocier: Optional[float] = Query(None),
    ticket_restaurant: Optional[str] = Query(None),
    mutuelle: Optional[str] = Query(None),
    code_commune: Optional[str] = Query(None),
    valeur_j9: Optional[str] = Query(None)
):
    # Log the received parameters
    logger.info(f"Received parameters: tjm={tjm}, jours_travailles={jours_travailles}, " +
                f"contract_type={contract_type}, frais_fonctionnement={frais_fonctionnement}, " +
                f"frais_gestion={frais_gestion}, provision_negocier={provision_negocier}, " +
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
        
        # Open the Excel file with xlwings - with events enabled
        app_excel = xw.App(visible=False, enable_events=True)
        app_excel.display_alerts = False
        app_excel.screen_updating = False
        
        # Try to open with specified path
        try:
            logger.info(f"Attempting to open Excel file: {temp_excel_path}")
            wb = app_excel.books.open(temp_excel_path)
            logger.info("Excel file opened successfully")
        except Exception as e:
            logger.error(f"Error opening Excel with absolute path: {str(e)}")
            return fallback_convert(
                tjm=tjm,
                jours_travailles=jours_travailles,
                contract_type=contract_type,
                frais_gestion=frais_gestion if frais_gestion is not None else 0,
                provision_negocier=provision_negocier if provision_negocier is not None else 0,
                ticket_restaurant=ticket_restaurant_bool,
                mutuelle=mutuelle_bool
            )

        try:
            # Get all sheet names for debugging
            sheet_names = [sheet.name for sheet in wb.sheets]
            logger.info(f"Excel sheets: {sheet_names}")
            
            # Look for the calculation sheet - try multiple possible names
            calculation_sheet_name = "1. Calcul Avec prov"
            if calculation_sheet_name not in sheet_names:
                for sheet_name in sheet_names:
                    if "calcul" in sheet_name.lower():
                        calculation_sheet_name = sheet_name
                        logger.info(f"Using alternative calculation sheet: {calculation_sheet_name}")
                        break
            
            # Access the calculation sheet
            ws = wb.sheets[calculation_sheet_name]
            
            # Fill in the data
            logger.info("Setting values in Excel...")
            
            # Initialiser la cellule B4 avec une valeur appropriée pour que GoalSeek fonctionne
            ws.range("B4").value = "BRUT"
            logger.info("Initialized cell B4 with value 'BRUT'")
            
            # Taux journalier
            ws.range("J4").value = tjm
            logger.info(f"Set TJM to {tjm} in cell J4")
            
            # Jours travaillés
            ws.range("J5").value = jours_travailles
            logger.info(f"Set jours travaillés to {jours_travailles} in cell J5")
            
            # Handle contract type
            if contract_type == "CDI":
                ws.range("J8").value = 0.02  # Fin de mission
                ws.range("J9").value = 0.1   # Montant congés payés
                ws.range("J10").value = 0    # Précarité
                
                # Ajouter la provision à négocier si elle est fournie
                if provision_negocier is not None:
                    ws.range("J11").value = provision_negocier / 100  # Convertir en format décimal pour Excel
                    logger.info(f"Set provision à négocier to {provision_negocier/100} in cell J11")
                
                logger.info(f"Set contract type to CDI")
            elif contract_type == "CDD":
                ws.range("J8").value = 0     # Fin de mission
                ws.range("J9").value = 0     # Montant congés payés
                ws.range("J10").value = 0.1  # Précarité
                logger.info("Set contract type to CDD")
            
            # Handle frais de gestion (J7)
            if frais_gestion is not None:
                ws.range("J7").value = frais_gestion / 100  # Diviser par 100 pour le format décimal
                logger.info(f"Set frais de gestion to {frais_gestion/100} in cell J7")
            
            # Handle frais de fonctionnement
            if frais_fonctionnement is not None:
                ws.range("J12").value = frais_fonctionnement  # Ne pas multiplier par 100
                logger.info(f"Set frais de fonctionnement to {frais_fonctionnement} in cell J12")
            
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
            
            # Handle code commune avec optimisation
            if code_commune:
                try:
                    # Vérifier d'abord si la feuille tauxTransport existe
                    transport_sheet_name = "tauxTransport 2025"  # Mise à jour pour 2025
                    
                    if transport_sheet_name in sheet_names:
                        transport_sheet = wb.sheets[transport_sheet_name]
                        
                        # Vérifier si le code commune est valide avec la méthode optimisée
                        start_time = time.time()
                        
                        if is_commune_code_valid(code_commune, transport_sheet):
                            logger.info(f"Code commune '{code_commune}' est valide")
                            ws.range("J25").value = code_commune
                            logger.info(f"Code commune appliqué dans cell J25")
                        else:
                            logger.warning(f"Code commune '{code_commune}' NON TROUVÉ dans la liste")
                            
                            # Lève une exception avec un message personnalisé
                            from fastapi.responses import JSONResponse
                            return JSONResponse(
                                status_code=400,
                                content={"message": "Le code Commune n'est pas dans la base de données"}
                            )
                            
                        end_time = time.time()
                        logger.info(f"Temps de vérification du code commune: {end_time - start_time:.2f} secondes")
                    else:
                        logger.warning(f"Feuille des taux de transport '{transport_sheet_name}' non trouvée, impossible de vérifier le code commune")
                except Exception as e:
                    logger.error(f"Erreur générale lors du traitement du code commune: {str(e)}")
            
            # Force calculation
            logger.info("Forcing Excel calculation...")
            wb.app.calculate()
            
            # Try to run the macro if it exists
            try:
                logger.info("Attempting to run macro...")
                
                # Implement TJM macro functionality directly to avoid errors
                ws.range("B12").value = tjm  # Valeur journalière = TJM
                ws.range("B10").value = tjm * jours_travailles  # Brut annuel = TJM * jours
                
                # Then try to run the actual macro - with error handling
                try:
                    wb.macro("TJM")()
                    logger.info("Successfully ran TJM macro")
                except Exception as e:
                    logger.warning(f"Error running TJM macro, but values were set directly: {str(e)}")
                    
                # Force calculation again to make sure all formulas are updated
                wb.app.calculate()
                
                # Try to run the UpdateTemplate macro if it exists
                try:
                    wb.macro("UpdateTemplate")()
                    logger.info("Successfully ran UpdateTemplate macro")
                except Exception as e:
                    logger.warning(f"Error running UpdateTemplate macro: {str(e)}")
                    # Try other common macro names
                    for macro_name in ["MAJ", "Calculate"]:
                        try:
                            wb.macro(macro_name)()
                            logger.info(f"Successfully ran {macro_name} macro")
                            break
                        except Exception as e2:
                            logger.warning(f"Error running {macro_name} macro: {str(e2)}")
                
                # Force calculation again
                wb.app.calculate()
                
            except Exception as e:
                logger.warning(f"Error in macro execution section: {str(e)}")
            
            # Look for template sheet for results
            template_sheet_name = "3. Template"
            if template_sheet_name not in sheet_names:
                for possible_name in ["Template", "Résultats", "Results"]:
                    if possible_name in sheet_names:
                        template_sheet_name = possible_name
                        logger.info(f"Using alternative template sheet: {template_sheet_name}")
                        break
                else:
                    template_sheet_name = calculation_sheet_name
                    logger.warning(f"Using calculation sheet as template: {template_sheet_name}")
            
            template_sheet = wb.sheets[template_sheet_name]
            
            # Debug: print values in key cells from both sheets
            debug_cells = {
                "template_sheet.E23": template_sheet.range("E23").value,
                "template_sheet.E26": template_sheet.range("E26").value,
                "template_sheet.E31": template_sheet.range("E31").value,
                "template_sheet.E8": template_sheet.range("E8").value,
                "calculation_sheet.B5": ws.range("B5").value,
                "calculation_sheet.B9": ws.range("B9").value,
                "calculation_sheet.E26": ws.range("E26").value
            }
            logger.info(f"Debug cell values: {debug_cells}")
            
            # Try to get results from different locations
            brut_mensuel = None
            net_mensuel = None
            frais_gestion_result = None
            
            # Try Template E26 (brut mensuel)
            if template_sheet.range("E26").value is not None:
                brut_mensuel = template_sheet.range("E26").value
                logger.info(f"Using E26 from template for brut_mensuel: {brut_mensuel}")
            # Try Template E31 (net mensuel)
            if template_sheet.range("E31").value is not None:
                net_mensuel = template_sheet.range("E31").value
                logger.info(f"Using E31 from template for net_mensuel: {net_mensuel}")
            # Try Template E10 (frais gestion)
            if template_sheet.range("E10").value is not None:
                frais_gestion_result = template_sheet.range("E10").value
                logger.info(f"Using E10 from template for frais_gestion: {frais_gestion_result}")
            
            # Get ticket and mutuelle contributions
            ticket_contribution = template_sheet.range("E21").value if ticket_restaurant_bool else 0
            mutuelle_contribution = template_sheet.range("E16").value if mutuelle_bool else 0
            
            # If template values not available, try calculation sheet
            if brut_mensuel is None:
                brut_mensuel = ws.range("B5").value
                logger.info(f"Using B5 from calculation for brut_mensuel: {brut_mensuel}")
            
            if net_mensuel is None:
                net_mensuel = ws.range("B9").value
                logger.info(f"Using B9 from calculation for net_mensuel: {net_mensuel}")
            
            if frais_gestion_result is None:
                frais_gestion_result = (ws.range("J7").value or 0) * brut_mensuel if brut_mensuel else 0
                logger.info(f"Calculated frais_gestion: {frais_gestion_result}")
                
            # Ensure we have values even if Excel reading fails
            if not brut_mensuel or brut_mensuel is None:
                brut_mensuel = tjm * jours_travailles
                logger.warning(f"Using fallback calculation for brut_mensuel: {brut_mensuel}")
            
            if not net_mensuel or net_mensuel is None:
                net_mensuel = brut_mensuel * 0.75  # Approximation
                logger.warning(f"Using fallback calculation for net_mensuel: {net_mensuel}")
            
            if not frais_gestion_result or frais_gestion_result is None:
                frais_gestion_result = brut_mensuel * (frais_gestion or 0) / 100
                logger.warning(f"Using fallback calculation for frais_gestion: {frais_gestion_result}")
            
            # Get Provision value
            provision_result = 0
            if contract_type == "CDI" and provision_negocier is not None:
                try:
                    provision_result = template_sheet.range("E23").value or 0
                    if not provision_result:
                        provision_result = brut_mensuel * (provision_negocier / 100)
                except Exception:
                    provision_result = brut_mensuel * (provision_negocier / 100)
            
            # Construct the result
            result = {
                "tjm": tjm,
                "brut_mensuel": brut_mensuel,
                "net_mensuel": net_mensuel,
                "frais_gestion": frais_gestion_result,
                "provision_negocier": provision_result,
                "autres_details": {
                    "ticket_restaurant_contribution": ticket_contribution or (jours_travailles * 5.5 if ticket_restaurant_bool else 0),
                    "mutuelle_contribution": mutuelle_contribution or (50 if mutuelle_bool else 0),
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
                logger.error(f"Error during Excel cleanup: {str(e)}")
    
    except Exception as e:
        error_msg = f"Excel processing error: {str(e)}"
        logger.error(error_msg)
        return fallback_convert(
            tjm=tjm,
            jours_travailles=jours_travailles,
            contract_type=contract_type,
            frais_gestion=frais_gestion if frais_gestion is not None else 0,
            provision_negocier=provision_negocier if provision_negocier is not None else 0,
            ticket_restaurant=ticket_restaurant_bool,
            mutuelle=mutuelle_bool
        )

@app.get("/preload-communes")
async def preload_communes():
    """Précharge les codes communes en mémoire pour accélérer les recherches futures"""
    try:
        # Import xlwings
        import xlwings as xw
        
        # Ouvrir le fichier Excel
        start_time = time.time()
        app_excel = xw.App(visible=False)
        app_excel.display_alerts = False
        
        wb = app_excel.books.open(EXCEL_TEMPLATE_PATH)
        logger.info("Excel file opened successfully for preloading communes")
        
        # Get sheet names
        sheet_names = [sheet.name for sheet in wb.sheets]
        
        # Check for transport sheet
        transport_sheet_name = "tauxTransport 2025"
        
        if transport_sheet_name in sheet_names:
            transport_sheet = wb.sheets[transport_sheet_name]
            
            # Charger les codes communes
            cache_key = "transport_codes"
            
            # Get the used range
            used_range = transport_sheet.used_range
            last_row = used_range.last_cell.row
            
            # Read codes in chunks for better performance
            codes_list = []
            chunk_size = 100
            
            for start_row in range(2, last_row + 1, chunk_size):
                end_row = min(start_row + chunk_size - 1, last_row)
                cell_range = f"A{start_row}:A{end_row}"
                
                # Read the chunk of values
                chunk_values = transport_sheet.range(cell_range).value
                
                # Handle single value case
                if not isinstance(chunk_values, list):
                    chunk_values = [chunk_values]
                
                # Process the values from the chunk
                for value in chunk_values:
                    if value is not None:
                        normalized_code = str(value).strip()
                        codes_list.append(normalized_code)
            
            COMMUNE_CODES_CACHE[cache_key] = codes_list
            
            end_time = time.time()
            logger.info(f"Preloaded {len(codes_list)} commune codes in {end_time - start_time:.2f} seconds")
            
            return {
                "status": "success", 
                "count": len(codes_list), 
                "time_seconds": end_time - start_time,
                "message": f"Successfully preloaded {len(codes_list)} commune codes"
            }
        else:
            return {"status": "error", "message": f"Transport sheet '{transport_sheet_name}' not found"}
    
    except Exception as e:
        logger.error(f"Error preloading communes: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        # Cleanup
        if 'wb' in locals() and wb:
            try:
                wb.close()
            except Exception:
                pass
        
        if 'app_excel' in locals() and app_excel:
            try:
                app_excel.quit()
            except Exception:
                pass

# Fallback endpoint that returns dummy data
@app.get("/fallback-convert")
def fallback_convert(
    tjm: Optional[float] = Query(500),
    jours_travailles: Optional[int] = Query(18),
    contract_type: Optional[str] = Query("CDI"),
    frais_gestion: Optional[float] = Query(0),
    provision_negocier: Optional[float] = Query(0),
    ticket_restaurant: Optional[bool] = Query(False),
    mutuelle: Optional[bool] = Query(False)
):
    """Fallback endpoint that returns calculated data when Excel fails"""
    brut_mensuel = tjm * jours_travailles
    frais_gestion_montant = brut_mensuel * (frais_gestion / 100) if frais_gestion else 0
    provision_negocier_montant = brut_mensuel * (provision_negocier / 100) if provision_negocier and contract_type == "CDI" else 0
    net_mensuel = brut_mensuel * 0.75  # Approximation simple du net
    
    return {
        "tjm": tjm,
        "brut_mensuel": brut_mensuel,
        "net_mensuel": net_mensuel,
        "frais_gestion": frais_gestion_montant,
        "provision_negocier": provision_negocier_montant,
        "autres_details": {
            "ticket_restaurant_contribution": jours_travailles * 5.5 if ticket_restaurant else 0,
            "mutuelle_contribution": 50 if mutuelle else 0,
        },
        "note": "Valeurs calculées (Excel non utilisé)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)