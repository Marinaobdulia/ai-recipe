"""
extract_recipes_to_csv.py
=========================
Extracts recipe ingredients from Notion and saves them to a CSV file.

Output CSV format:
  - Column 1: Recipe Title
  - Column 2: Ingredients (comma-separated)

Usage:
  python extract_recipes_to_csv.py [output_filename.csv]

Example:
  python extract_recipes_to_csv.py recipes_ingredients.csv
"""

import os
import sys
import csv
import re
import requests
from typing import List, Optional
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from tools.notion_tools import get_recipe_list, get_recipe_details


def extract_url_from_body(body: str) -> Optional[str]:
    """
    Extracts the first URL found in the recipe body content.
    
    Args:
        body: Full recipe content from Notion
    
    Returns:
        URL string if found, None otherwise
    """
    url_pattern = r'https?://[^\s]+'
    match = re.search(url_pattern, body)
    return match.group(0) if match else None


def extract_ingredients_from_url(url: str) -> str:
    """
    Fetches a recipe URL and extracts ingredients from the HTML content.
    
    Looks for common ingredient patterns in HTML:
    - Lists, divs, or spans with "ingredient" in their class or id
    - Text following "ingredientes" or "ingredients" headers
    
    Args:
        url: URL to fetch and parse
    
    Returns:
        Comma-separated string of ingredients, or error message
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        ingredients = []
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Look for ingredients in common HTML structures
        # Try finding elements with "ingredient" in class or id
        ingredient_containers = soup.find_all(
            ['ul', 'ol', 'div'],
            {'class': re.compile(r'ingredien', re.I)}
        )
        
        if ingredient_containers:
            for container in ingredient_containers:
                items = container.find_all(['li', 'div', 'p'])
                for item in items:
                    text = item.get_text(strip=True)
                    if text and len(text) > 3:  # Avoid very short text
                        ingredients.append(text)
        
        # If no ingredients found with class matching, try finding by section header
        if not ingredients:
            text = soup.get_text(separator='\n')
            lines = text.split('\n')
            
            in_ingredients = False
            for line in lines:
                line_lower = line.lower().strip()
                
                if any(header in line_lower for header in ['ingrediente', 'ingredient', 'ingredientes']):
                    in_ingredients = True
                    continue
                
                if in_ingredients:
                    if any(header in line_lower for header in ['instrucción', 'instruction', 'preparación', 'preparation', 'elaboración', 'modo de preparar', 'pasos']):
                        break
                    
                    cleaned = re.sub(r'^[•\-*\d\.\)\s]+', '', line.strip())
                    if cleaned and len(cleaned) > 3:
                        ingredients.append(cleaned)
        
        return ", ".join(ingredients) if ingredients else "(No ingredients found on page)"
        
    except requests.RequestException as e:
        return f"(Could not fetch URL: {str(e)[:50]})"
    except Exception as e:
        return f"(Error parsing URL: {str(e)[:50]})"


def extract_ingredients_from_body(body: str) -> str:
    """
    Extracts ingredients from the recipe body content.
    
    Looks for common ingredient section patterns:
    - Text after "Ingredientes:" or "Ingredients:"
    - Lines starting with bullets (•) or dashes (-)
    - Takes content until instructions section or end of body
    
    Args:
        body: Full recipe content from Notion
    
    Returns:
        Comma-separated string of ingredients
    """
    if not body.strip():
        return ""
    
    lines = body.split('\n')
    ingredients = []
    in_ingredients_section = False
    
    # Look for ingredients section header
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        # Check if this is an ingredients section header
        if any(header in line_lower for header in ['ingrediente', 'ingredient', 'ingredientes']):
            in_ingredients_section = True
            continue
        
        # Check if we've reached instructions or other section
        if in_ingredients_section and any(header in line_lower for header in 
                                          ['instrucción', 'instrucciones', 'instruction', 'preparación', 'preparation',
                                           'elaboración', 'modo de preparar', 'pasos', 'receta']):
            break
        
        # Collect ingredient lines
        if in_ingredients_section:
            # Remove bullet points and dashes
            cleaned = re.sub(r'^[\s•\-\[\s\]]+', '', line.strip())
            
            if cleaned and not cleaned.startswith('['):  # Skip checkbox markers
                ingredients.append(cleaned)
    
    # If no explicit ingredients section found, collect all bulleted items
    if not ingredients:
        for line in lines:
            # Match lines starting with bullet or dash (common ingredient format)
            if re.match(r'^\s*[•\-]\s+', line):
                cleaned = re.sub(r'^[\s•\-]+', '', line.strip())
                if cleaned:
                    ingredients.append(cleaned)
    
    # If still no ingredients, check if body contains a URL
    if not ingredients:
        url = extract_url_from_body(body)
        if url:
            return extract_ingredients_from_url(url)
        return ""
    
    # Join with comma and clean up
    result = ", ".join(ingredients)
    return result


def main(output_csv: str = "recipes_ingredients.csv"):
    """
    Main function to extract all recipes and save to CSV.
    
    Args:
        output_csv: Output CSV filename (default: recipes_ingredients.csv)
    """
    load_dotenv()
    
    print("📋 Fetching recipe list...")
    recipe_list_str = get_recipe_list.invoke({})
    
    if "Error" in recipe_list_str or "No recipes" in recipe_list_str:
        print(f"❌ {recipe_list_str}")
        return
    
    recipe_names = [name.strip() for name in recipe_list_str.split(",")]
    print(f"✅ Found {len(recipe_names)} recipes\n")
    
    recipes_data = []
    
    for i, recipe_name in enumerate(recipe_names, 1):
        print(f"[{i}/{len(recipe_names)}] Processing: {recipe_name}...", end=" ")
        
        try:
            details = get_recipe_details.invoke({"recipe_name": recipe_name})
            
            # Parse title and body
            parts = details.split('\n', 1)
            title = parts[0].strip()
            body = parts[1] if len(parts) > 1 else ""
            
            # Extract ingredients
            ingredients = extract_ingredients_from_body(body)
            num_ingredients = len([i for i in ingredients.split(',') if i.strip()]) if ingredients else 0
            
            recipes_data.append({
                'title': title,
                'ingredients': ingredients
            })
            
            print(f"✓ ({num_ingredients} ingredients)")
            
        except Exception as e:
            print(f"❌ Error: {str(e)[:60]}")
            recipes_data.append({
                'title': recipe_name,
                'ingredients': "(Error extracting ingredients)"
            })
    
    # Write to CSV
    print(f"\n💾 Saving to {output_csv}...")
    
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Recipe Title', 'Ingredients']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for recipe in recipes_data:
                writer.writerow({
                    'Recipe Title': recipe['title'],
                    'Ingredients': recipe['ingredients']
                })
        
        print(f"✅ Successfully saved {len(recipes_data)} recipes to {output_csv}")
        
    except Exception as e:
        print(f"❌ Error writing CSV: {e}")


if __name__ == "__main__":
    # Get output filename from command line or use default
    output_file = sys.argv[1] if len(sys.argv) > 1 else "recipes_ingredients.csv"
    
    main(output_csv=output_file)
