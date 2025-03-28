import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';

interface CalculationResult {
  tjm: number;
  brut_mensuel: number;
  net_mensuel: number;
  frais_gestion: number;
  autres_details: {
    ticket_restaurant_contribution: number;
    mutuelle_contribution: number;
  };
}

@Component({
  selector: 'app-calculator',
  standalone: false,
  templateUrl: './calculator.component.html',
  styleUrls: ['./calculator.component.css']
})
export class CalculatorComponent implements OnInit {
  // Parameters for the form
  parameters = {
    tjm: 500, // Default TJM value
    joursTravailles: 18, // Default: 18 days
    contractType: 'CDI', // Default: CDI
    fraisFonctionnement: 0, // Default: 8%
    ticketRestaurant: false,
    mutuelle: false,
    codeCommune: ''
  };

  // Backend API URL
  private apiUrl = 'http://127.0.0.1:8000/convert';
  
  // Result object
  result: CalculationResult | null = null;
  isLoading: boolean = false;
  errorMessage: string | null = null;
  debugMode: boolean = false; // Set to true to see raw API response
  
  constructor(private http: HttpClient) {}
  
  ngOnInit(): void {
    // You could load saved preferences here if needed
  }

  // Format currency values for display
  formatCurrency(value: any): string {
    if (value === null || value === undefined) {
      return 'N/A';
    }
    
    // Handle various formats that might come from Excel
    let numValue: number;
    
    if (typeof value === 'string') {
      // Remove any currency symbols or spaces
      const cleanValue = value.replace(/[^0-9.,]/g, '').replace(',', '.');
      numValue = parseFloat(cleanValue);
    } else {
      numValue = Number(value);
    }
    
    if (isNaN(numValue)) {
      return 'N/A';
    }
    
    return numValue.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
  }
  
  // Toggle debug mode
  toggleDebugMode(): void {
    this.debugMode = !this.debugMode;
  }

  // Call the backend API
  calculate(): void {
    // Validate inputs before making API call
    if (this.parameters.tjm < 290) {
      this.errorMessage = "Le taux journalier doit être supérieur à 289.";
      return;
    }
    
    if (this.parameters.joursTravailles <= 0 || this.parameters.joursTravailles > 30) {
      this.errorMessage = "Le nombre de jours travaillés doit être entre 1 et 30.";
      return;
    }
    
    this.errorMessage = null;
    this.isLoading = true;
    
    // Use HttpParams for better query parameter handling
    let params = new HttpParams()
      .set('tjm', this.parameters.tjm.toString())
      .set('jours_travailles', this.parameters.joursTravailles.toString())
      .set('contract_type', this.parameters.contractType)
      .set('frais_fonctionnement', (this.parameters.fraisFonctionnement / 100).toString());
    
    // Only add optional parameters if they have values
    if (this.parameters.ticketRestaurant) {
      params = params.set('ticket_restaurant', 'true');
    } else {
      params = params.set('ticket_restaurant', 'false');
    }
    
    if (this.parameters.mutuelle) {
      params = params.set('mutuelle', 'true');
    } else {
      params = params.set('mutuelle', 'false'); 
    }
    
    if (this.parameters.codeCommune) {
      params = params.set('code_commune', this.parameters.codeCommune);
    }
    
    // Log the URL that will be called for debugging
    const fullUrl = `${this.apiUrl}?${params.toString()}`;
    console.log('Calling API URL:', fullUrl);

    // Make the HTTP request with properly formatted params
    this.http.get<CalculationResult>(this.apiUrl, { params }).subscribe({
      next: (response: CalculationResult) => {
        this.result = response;
        this.isLoading = false;
        console.log('Calculation result:', this.result);
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        
        // Create a user-friendly error message
        if (error.error && error.error.detail) {
          if (error.error.detail.includes("Excel")) {
            this.errorMessage = "Une erreur s'est produite lors de la communication avec Excel. Détail: " + error.error.detail;
          } else {
            this.errorMessage = "Une erreur s'est produite lors de la communication avec le serveur. Détail: " + error.error.detail;
          }
        } else {
          this.errorMessage = "Une erreur s'est produite lors de la communication avec le serveur. Veuillez réessayer.";
        }
        
        console.error('Error calling backend API:', error);
      }
    });
  }
  
  // Reset the form to defaults
  resetForm(): void {
    this.parameters = {
      tjm: 500,
      joursTravailles: 18,
      contractType: 'CDI',
      fraisFonctionnement: 0,
      ticketRestaurant: false,
      mutuelle: false,
      codeCommune: ''
    };
    this.result = null;
    this.errorMessage = null;
  }
}