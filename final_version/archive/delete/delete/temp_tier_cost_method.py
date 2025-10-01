    def _calculate_single_tier_cost(self, supplier_depot_id: int, option: str, tier_name: str) -> float:
        """
        Calculate tier cost for a single option using volume tier rebate.
        
        Args:
            supplier_depot_id: Supplier depot ID
            option: Option name (e.g., 'coc_30')
            tier_name: Volume tier configuration name
            
        Returns:
            Cost per litre using volume tier rebate, or None if not applicable
        """
        if self.raw_data is None:
            return None
            
        # Find the raw data row for this supplier depot
        matching_rows = self.raw_data[self.raw_data['Supplier_Depot_FK'] == supplier_depot_id]
        if matching_rows.empty:
            return None
            
        row = matching_rows.iloc[0]
        
        # Get tier configuration
        tier_config = self.config['volume_tier_configurations'][tier_name]
        combination_rule = tier_config.get('combination_rule', {}).get('with_base_rebates', 'add')
        
        # Get volume tier rebate rate (flat rate for tier costing)
        tier_bands = tier_config['tiers']['bands']
        tier_rebate_rate = 0.0
        
        # For tier costing, use the highest tier rate available
        for band in tier_bands:
            if band['rebate'] > 0:
                tier_rebate_rate = band['rebate']
        
        if tier_rebate_rate == 0:
            return None
            
        # Apply PV discount to tier rebate (all volume tier rebates are NET30)
        pv_factors = self.calculate_present_value_factors()
        tier_rebate_pv = tier_rebate_rate / pv_factors['net30']
        
        # Calculate tier cost using correct formula
        wholesale_price = row['rtl_wholesale'] / 100  # Convert from cents to rands
        
        # Get cost components
        cost_components = self._decompose_base_cost_components(row, option)
        if cost_components is None:
            return None
            
        # Apply combination rule
        if combination_rule == 'override':
            # Override: wholesale_price - tier_rebate_pv + transport + equipment
            final_cost = (wholesale_price - tier_rebate_pv + 
                         cost_components['transport_cost'] + 
                         cost_components['equipment_cost'])
        elif combination_rule == 'add':
            # Add: wholesale_price - (base_rebate_pv + tier_rebate_pv) + transport + equipment
            base_rebate_pv = cost_components['base_rebate_pv']
            final_cost = (wholesale_price - (base_rebate_pv + tier_rebate_pv) + 
                         cost_components['transport_cost'] + 
                         cost_components['equipment_cost'])
        else:
            return None
            
        return final_cost