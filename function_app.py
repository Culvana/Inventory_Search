import azure.functions as func
import azure.cosmos as cosmos
import json
import logging
import os
from typing import List, Dict, Any, Optional

# Initialize the Function App
myapp = func.FunctionApp()

# CosmosDB configuration
COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT')
COSMOS_KEY = os.environ.get('COSMOS_KEY')
COSMOS_DATABASE = 'InvoicesDB'
COSMOS_CONTAINER ='Inventory'

# Initialize CosmosDB client
cosmos_client = cosmos.CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.get_database_client(COSMOS_DATABASE)
container = database.get_container_client(COSMOS_CONTAINER)

@myapp.route(route="inventory/{user_id}/search", methods=["GET"])
def search_inventory(req: func.HttpRequest) -> func.HttpResponse:
    """
    Smart search inventory items by user ID and any search term
    Path parameters:
    - user_id (required): User ID to filter items
    Query parameters:
    - q (optional): Search term - searches across all fields (name, category, supplier, item number, etc.)
    """
    logging.info('Processing inventory search request')
    
    try:
        # Get path and query parameters
        user_id = req.route_params.get('user_id')
        search_term = req.params.get('q', '').strip()
        
        # Validate required parameters
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id parameter is required in URL path"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # If no search term, return all inventory
        if not search_term:
            query = "SELECT * FROM c WHERE c.userId = @userId ORDER BY c.timestamp DESC"
            parameters = [{"name": "@userId", "value": user_id}]
        else:
            # Smart search across all relevant fields
            query = """
                SELECT * FROM c 
                WHERE c.userId = @userId 
                AND (
                    CONTAINS(UPPER(c.supplier_name), UPPER(@searchTerm))
                    OR EXISTS(
                        SELECT VALUE item FROM item IN c.items 
                        WHERE CONTAINS(UPPER(item['Inventory Item Name']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Item Name']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Category']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Item Number']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Supplier Name']), UPPER(@searchTerm))
                    )
                )
                ORDER BY c.timestamp DESC
            """
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@searchTerm", "value": search_term}
            ]
        
        # Execute query
        documents = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        # Return complete document structure but only with matched items
        results = []
        total_items_found = 0
        
        for doc in documents:
            if search_term:
                # Filter to only include matching items
                matching_items = []
                search_upper = search_term.upper()
                
                for item in doc.get('items', []):
                    if (search_upper in item.get('Inventory Item Name', '').upper() or
                        search_upper in item.get('Item Name', '').upper() or
                        search_upper in item.get('Category', '').upper() or
                        search_upper in item.get('Item Number', '').upper() or
                        search_upper in item.get('Supplier Name', '').upper() or
                        search_upper in item.get('Measured In', '').upper() or
                        search_upper in item.get('Inventory Unit of Measure', '').upper() or
                        search_upper in doc.get('supplier_name', '').upper()):
                        matching_items.append(item)
                
                if matching_items:
                    # Return complete document structure with only matching items
                    result_doc = {
                        "id": doc.get('id'),
                        "userId": doc.get('userId'),
                        "supplier_name": doc.get('supplier_name'),
                        "timestamp": doc.get('timestamp'),
                        "batchNumber": doc.get('batchNumber'),
                        "total_items_in_original_document": len(doc.get('items', [])),
                        "matched_items_count": len(matching_items),
                        "items": matching_items  # Only matched items
                    }
                    results.append(result_doc)
                    total_items_found += len(matching_items)
            else:
                # Return all items if no search term
                result_doc = {
                    "id": doc.get('id'),
                    "userId": doc.get('userId'),
                    "supplier_name": doc.get('supplier_name'),
                    "timestamp": doc.get('timestamp'),
                    "batchNumber": doc.get('batchNumber'),
                    "total_items_in_document": len(doc.get('items', [])),
                    "items": doc.get('items', [])
                }
                results.append(result_doc)
                total_items_found += len(doc.get('items', []))
        
        response_data = {
            "user_id": user_id,
            "search_term": search_term if search_term else "all",
            "documents_found": len(results),
            "total_items_found": total_items_found,
            "documents": results
        }
        
        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in search_inventory: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

@myapp.route(route="inventory/{user_id}", methods=["GET"])
def get_inventory(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get inventory with optional search - simpler endpoint
    Path parameters:
    - user_id (required): User ID to filter items
    Query parameters:
    - q (optional): Any search term (dry grocery, chicken, etc.)
    """
    logging.info('Processing inventory request')
    
    try:
        user_id = req.route_params.get('user_id')
        search_term = req.params.get('q', '').strip()
        
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id parameter is required in URL path"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Build query based on whether search term is provided
        if not search_term:
            # Return all inventory
            query = "SELECT * FROM c WHERE c.userId = @userId ORDER BY c.timestamp DESC"
            parameters = [{"name": "@userId", "value": user_id}]
        else:
            # Smart search across all fields
            query = """
                SELECT * FROM c 
                WHERE c.userId = @userId 
                AND (
                    CONTAINS(UPPER(c.supplier_name), UPPER(@searchTerm))
                    OR EXISTS(
                        SELECT VALUE item FROM item IN c.items 
                        WHERE CONTAINS(UPPER(item['Inventory Item Name']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Item Name']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Category']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Item Number']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Supplier Name']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Measured In']), UPPER(@searchTerm))
                        OR CONTAINS(UPPER(item['Inventory Unit of Measure']), UPPER(@searchTerm))
                    )
                )
                ORDER BY c.timestamp DESC
            """
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@searchTerm", "value": search_term}
            ]
        
        # Execute query
        documents = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        # Return complete document structure but only with matched items
        results = []
        total_matching_items = 0
        
        for doc in documents:
            if search_term:
                # Filter to only include matching items
                matching_items = []
                search_upper = search_term.upper()
                
                for item in doc.get('items', []):
                    # Check if item matches search term
                    if (search_upper in item.get('Inventory Item Name', '').upper() or
                        search_upper in item.get('Item Name', '').upper() or
                        search_upper in item.get('Category', '').upper() or
                        search_upper in item.get('Item Number', '').upper() or
                        search_upper in item.get('Supplier Name', '').upper() or
                        search_upper in item.get('Measured In', '').upper() or
                        search_upper in item.get('Inventory Unit of Measure', '').upper() or
                        search_upper in doc.get('supplier_name', '').upper()):
                        matching_items.append(item)
                
                if matching_items:
                    # Return complete document structure with only matching items
                    result_doc = {
                        "document_id": doc.get('id'),
                        "user_id": doc.get('userId'),
                        "supplier_name": doc.get('supplier_name'),
                        "timestamp": doc.get('timestamp'),
                        "batchNumber": doc.get('batchNumber'),
                        "total_items_in_original_document": len(doc.get('items', [])),
                        "matched_items_count": len(matching_items),
                        "items": matching_items  # Only matched items
                    }
                    results.append(result_doc)
                    total_matching_items += len(matching_items)
            else:
                # Return all items if no search term
                result_doc = {
                    "document_id": doc.get('id'),
                    "user_id": doc.get('userId'),
                    "supplier_name": doc.get('supplier_name'),
                    "timestamp": doc.get('timestamp'),
                    "batchNumber": doc.get('batchNumber'),
                    "total_items_in_document": len(doc.get('items', [])),
                    "items": doc.get('items', [])
                }
                results.append(result_doc)
                total_matching_items += len(doc.get('items', []))
        
        # Create response
        response_data = {
            "user_id": user_id,
            "search_query": search_term if search_term else "all inventory",
            "results_summary": {
                "documents_found": len(results),
                "total_items": total_matching_items
            },
            "inventory": results
        }
        
        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in get_inventory: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

@myapp.route(route="inventory/{user_id}/stats", methods=["GET"])
def get_inventory_stats(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get inventory statistics for a user
    Path parameters:
    - user_id (required): User ID
    """
    logging.info('Processing inventory stats request')
    
    try:
        user_id = req.route_params.get('user_id')
        
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id parameter is required in URL path"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get all documents
        query = "SELECT * FROM c WHERE c.userId = @userId"
        parameters = [{"name": "@userId", "value": user_id}]
        
        documents = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        # Calculate stats
        total_items = 0
        categories = {}
        suppliers = set()
        total_value = 0.0
        
        for doc in documents:
            suppliers.add(doc.get('supplier_name'))
            for item in doc.get('items', []):
                total_items += 1
                category = item.get('Category', 'Unknown')
                
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1
                
                case_price = item.get('Case Price', 0)
                if isinstance(case_price, (int, float)):
                    total_value += case_price
        
        stats = {
            "user_id": user_id,
            "total_documents": len(documents),
            "total_items": total_items,
            "total_categories": len(categories),
            "total_suppliers": len(suppliers),
            "total_inventory_value": round(total_value, 2),
            "categories": categories,
            "suppliers": list(suppliers)
        }
        
        return func.HttpResponse(
            json.dumps(stats, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in get_inventory_stats: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )