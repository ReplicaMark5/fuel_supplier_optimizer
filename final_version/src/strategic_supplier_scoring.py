#!/usr/bin/env python3
"""
Strategic Supplier Scoring Module

This module provides functions to calculate weighted strategic supplier scores
from the database for use in multi-objective optimization.
"""

import sqlite3
import logging
from typing import Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StrategicSupplierScoring:
    """Class to handle strategic supplier scoring calculations."""
    
    def __init__(self, db_path: str = str(Path(__file__).resolve().parents[1] / "data/databases/fuel_data.db")):
        """Initialize with database path."""
        self.db_path = db_path
        self.supplier_scores = {}
        self.criteria_weights = {}
        self._load_data()
    
    def _load_data(self):
        """Load supplier scores and criteria weights from database."""
        logger.info("Loading strategic supplier scores and criteria weights from database...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Load criteria weights
                cursor.execute("""
                    SELECT criteria_name, weight 
                    FROM criteria_weights 
                    ORDER BY criteria_name
                """)
                
                for criteria_name, weight in cursor.fetchall():
                    self.criteria_weights[criteria_name] = weight
                
                # Load supplier scores
                cursor.execute("""
                    SELECT supplier_name, current_level, product_service_type,
                           geographical_network, method_of_sourcing,
                           invest_refuelling_equipment, reciprocal_business
                    FROM supplier_scores
                    ORDER BY supplier_name
                """)
                
                for row in cursor.fetchall():
                    supplier_name = row[0]
                    self.supplier_scores[supplier_name] = {
                        'Current Level (1-8)': row[1],
                        'Product / Service Type': row[2],
                        'Geographical Network': row[3],
                        'Method of Sourcing': row[4],
                        'Invest in Refuelling Equipment': row[5],
                        'Reciprocal Business': row[6]
                    }
                
                logger.info(f"Loaded {len(self.criteria_weights)} criteria weights and {len(self.supplier_scores)} supplier scores")
                
        except sqlite3.Error as e:
            logger.error(f"Database error loading strategic supplier data: {e}")
            raise
    
    def calculate_supplier_strategic_score(self, supplier_name: str) -> float:
        """
        Calculate weighted strategic score for a single supplier.
        
        Args:
            supplier_name: Name of the supplier
            
        Returns:
            float: Weighted strategic score (0.0 to 1.0)
        """
        if supplier_name not in self.supplier_scores:
            logger.warning(f"Supplier '{supplier_name}' not found in strategic scores database")
            return 0.0
        
        supplier_data = self.supplier_scores[supplier_name]
        weighted_score = 0.0
        
        for criteria_name, weight in self.criteria_weights.items():
            if criteria_name in supplier_data:
                criterion_score = supplier_data[criteria_name]
                weighted_score += criterion_score * weight
                
        logger.debug(f"Strategic score for {supplier_name}: {weighted_score:.4f}")
        return weighted_score
    
    def get_all_supplier_strategic_scores(self) -> Dict[str, float]:
        """
        Get strategic scores for all suppliers.
        
        Returns:
            Dict mapping supplier names to their strategic scores
        """
        scores = {}
        for supplier_name in self.supplier_scores.keys():
            scores[supplier_name] = self.calculate_supplier_strategic_score(supplier_name)
        
        logger.info(f"Calculated strategic scores for {len(scores)} suppliers")
        return scores
    
    def get_supplier_score_by_id(self, supplier_id: int, supplier_id_to_name: Dict[int, str]) -> float:
        """
        Get strategic score for a supplier by ID.
        
        Args:
            supplier_id: Supplier ID
            supplier_id_to_name: Mapping from supplier ID to name
            
        Returns:
            float: Strategic score for the supplier
        """
        if supplier_id not in supplier_id_to_name:
            logger.warning(f"Supplier ID {supplier_id} not found in mapping")
            return 0.0
            
        supplier_name = supplier_id_to_name[supplier_id]
        return self.calculate_supplier_strategic_score(supplier_name)
    
    def display_supplier_rankings(self):
        """Display suppliers ranked by strategic score."""
        scores = self.get_all_supplier_strategic_scores()
        sorted_suppliers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        logger.info("Strategic Supplier Rankings:")
        for i, (supplier_name, score) in enumerate(sorted_suppliers, 1):
            logger.info(f"  {i}. {supplier_name}: {score:.4f}")
        
        return sorted_suppliers


def test_strategic_scoring():
    """Test function for strategic supplier scoring."""
    logger.info("Testing strategic supplier scoring...")
    
    # Initialize scoring system
    scoring = StrategicSupplierScoring()
    
    # Display criteria weights
    logger.info("Criteria Weights:")
    for criteria, weight in scoring.criteria_weights.items():
        logger.info(f"  {criteria}: {weight}")
    
    # Display supplier rankings
    scoring.display_supplier_rankings()
    
    # Test individual supplier lookup
    test_supplier = "Supplier A"
    score = scoring.calculate_supplier_strategic_score(test_supplier)
    logger.info(f"Test score for {test_supplier}: {score:.4f}")


if __name__ == "__main__":
    test_strategic_scoring()
