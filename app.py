import os
import streamlit as st
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import sqlite3
from pathlib import Path
import requests
import json
from datetime import datetime

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ dotenv loaded successfully")
except ImportError:
    # python-dotenv not available, use system environment variables
    print("⚠️ python-dotenv not available, using system environment variables")
    pass

# Set up logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration class with proper boolean handling"""
    mistral_api_key: str
    exa_api_key: str
    firecrawl_api_key: Optional[str]
    database_url: str
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables with proper type conversion"""
        mistral_key = os.getenv('MISTRAL_API_KEY', '')
        exa_key = os.getenv('EXA_API_KEY', '')
        
        # Debug environment variable loading
        print(f"🔍 Environment Variables Debug:")
        print(f"   MISTRAL_API_KEY loaded: {'Yes' if mistral_key else 'No'} (length: {len(mistral_key)})")
        print(f"   EXA_API_KEY loaded: {'Yes' if exa_key else 'No'} (length: {len(exa_key)})")
        
        # Validate Mistral API key format (32-character alphanumeric)
        if mistral_key and (len(mistral_key) != 32 or not mistral_key.isalnum()):
            print(f"⚠️ WARNING: Mistral API key should be 32-character alphanumeric. Current format: {mistral_key[:10]}...")
            print(f"   This may cause authentication errors. Please check your key from https://console.mistral.ai/")
        
        return cls(
            mistral_api_key=mistral_key,
            exa_api_key=exa_key,
            firecrawl_api_key=os.getenv('FIRECRAWL_API_KEY'),
            database_url=os.getenv('DATABASE_URL', 'nutrisense_data.db'),
            qdrant_url=os.getenv('QDRANT_URL', ''),
            qdrant_api_key=os.getenv('QDRANT_API_KEY', ''),
            qdrant_collection=os.getenv('QDRANT_COLLECTION', 'nutrisense_memories')
        ) 

class NutrisenseAssistant:
    """Main assistant class with proper error handling"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_path = Path(config.database_url)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with user preferences support"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Existing nutrition logs table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS nutrition_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        food_item TEXT,
                        calories REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # User preferences table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT UNIQUE,
                        dietary_restrictions TEXT,  -- JSON array of restrictions
                        food_allergies TEXT,        -- JSON array of allergies
                        cuisine_preferences TEXT,   -- JSON array of preferred cuisines
                        health_goals TEXT,          -- JSON object with goals
                        weight_goal REAL,           -- Target weight
                        current_weight REAL,        -- Current weight
                        activity_level TEXT,        -- sedentary, light, moderate, active, very_active
                        age INTEGER,
                        gender TEXT,
                        height_cm REAL,
                        daily_calorie_target INTEGER,
                        protein_target REAL,
                        carb_target REAL,
                        fat_target REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def validate_input(self, user_input: str) -> bool:
        """Validate user input with proper boolean handling"""
        if not user_input or not isinstance(user_input, str):
            return False
        
        # Common fix for boolean iteration error
        forbidden_words = ['spam', 'abuse', 'illegal']  # This should be a list
        
        # Check if any forbidden word is in the input
        return not any(word in user_input.lower() for word in forbidden_words)
    
    def save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> str:
        """Save or update user preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Convert lists/dicts to JSON strings
                dietary_restrictions = json.dumps(preferences.get('dietary_restrictions', []))
                food_allergies = json.dumps(preferences.get('food_allergies', []))
                cuisine_preferences = json.dumps(preferences.get('cuisine_preferences', []))
                health_goals = json.dumps(preferences.get('health_goals', {}))
                
                # Use INSERT OR REPLACE to handle updates
                conn.execute('''
                    INSERT OR REPLACE INTO user_preferences 
                    (user_id, dietary_restrictions, food_allergies, cuisine_preferences, 
                     health_goals, weight_goal, current_weight, activity_level, age, 
                     gender, height_cm, daily_calorie_target, protein_target, 
                     carb_target, fat_target, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    user_id, dietary_restrictions, food_allergies, cuisine_preferences,
                    health_goals, preferences.get('weight_goal'), preferences.get('current_weight'),
                    preferences.get('activity_level'), preferences.get('age'),
                    preferences.get('gender'), preferences.get('height_cm'),
                    preferences.get('daily_calorie_target'), preferences.get('protein_target'),
                    preferences.get('carb_target'), preferences.get('fat_target')
                ))
                conn.commit()
                return "✅ Preferences saved successfully!"
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            return f"❌ Error saving preferences: {str(e)}"
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Retrieve user preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return {}
                
                # Convert row to dict
                columns = [desc[0] for desc in cursor.description]
                preferences = dict(zip(columns, row))
                
                # Parse JSON fields
                try:
                    preferences['dietary_restrictions'] = json.loads(preferences.get('dietary_restrictions', '[]'))
                    preferences['food_allergies'] = json.loads(preferences.get('food_allergies', '[]'))
                    preferences['cuisine_preferences'] = json.loads(preferences.get('cuisine_preferences', '[]'))
                    preferences['health_goals'] = json.loads(preferences.get('health_goals', '{}'))
                except json.JSONDecodeError:
                    logger.warning(f"JSON decode error for user {user_id} preferences")
                
                return preferences
                
        except Exception as e:
            logger.error(f"Error retrieving preferences: {e}")
            return {}
    
    def _generate_smart_search_queries(self, location: str, user_prefs: Dict[str, Any], cuisine: str = "") -> List[str]:
        """Generate intelligent search queries using Mistral Agents API based on user preferences, with fallback"""
        
        # Try AI-powered query generation first
        if self.config.mistral_api_key:
            try:
                # Build context about user preferences
                context_parts = [f"Location: {location}"]
                
                if cuisine:                   
                    context_parts.append(f"Cuisine preference: {cuisine}")
                
                if user_prefs.get('dietary_restrictions'):
                    dietary_list = ', '.join(user_prefs['dietary_restrictions'])
                    context_parts.append(f"Dietary restrictions: {dietary_list}")
                
                if user_prefs.get('food_allergies'):
                    allergy_list = ', '.join(user_prefs['food_allergies'])
                    context_parts.append(f"Food allergies: {allergy_list}")
                
                if user_prefs.get('health_goals'):
                    goals = [k.replace('_', ' ') for k, v in user_prefs['health_goals'].items() if v]
                    if goals:
                        context_parts.append(f"Health goals: {', '.join(goals)}")
                
                context = '. '.join(context_parts)
                
                # Call Mistral Agents API
                headers = {
                    "Authorization": f"Bearer {self.config.mistral_api_key}",
                    "Content-Type": "application/json"
                }
                
                # Agents API payload structure
                payload = {
                    "model": "mistral-large-latest",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert at generating effective search queries for finding restaurants that match specific user needs and preferences."
                        },
                        {
                            "role": "user",
                            "content": f"""Based on the following user context, generate 3 diverse and effective search queries to find restaurants that match their needs:

{context}

Generate 3 different search queries that would find relevant restaurants. Each query should:
1. Be specific and targeted for web search
2. Include the location
3. Incorporate the user's dietary needs naturally
4. Use different search strategies (broad, specific, health-focused)

Format: Return only the 3 queries, one per line, no numbering or bullets.

Example format:
best vegetarian restaurants in Mumbai for weight loss
Mumbai healthy dining gluten-free options reviews
vegetarian restaurants Mumbai nutritious meals"""
                        }
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "stream": False
                }
                
                response = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",  # Agents API uses same endpoint but different payload structure
                    headers=headers,
                    json=payload,
                    timeout=20
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content'].strip()
                    queries = [q.strip() for q in content.split('\n') if q.strip()]
                    
                    if len(queries) >= 3:
                        logger.info(f"✅ Generated {len(queries)} smart search queries using Mistral Agents API")
                        return queries[:3]
                    else:
                        logger.warning(f"⚠️ AI generated only {len(queries)} queries, falling back to basic queries")
                else:
                    logger.warning(f"⚠️ Mistral Agents API failed with status {response.status_code}, falling back to basic queries")
                    
            except Exception as e:
                logger.warning(f"⚠️ Mistral Agents API error: {e}, falling back to basic queries")
        
        # Fallback to basic query generation when AI is not available or fails
        logger.info("🔄 Using fallback query generation (AI not available)")
        return self._generate_fallback_queries(location, user_prefs, cuisine)
    
    def _generate_fallback_queries(self, location: str, user_prefs: Dict[str, Any], cuisine: str = "") -> List[str]:
        """Generate basic search queries when AI is not available"""
        queries = []
        
        # Build dietary restriction string
        dietary_terms = []
        if user_prefs.get('dietary_restrictions'):
            for restriction in user_prefs['dietary_restrictions']:
                if 'vegetarian' in restriction.lower():
                    dietary_terms.append('vegetarian')
                elif 'vegan' in restriction.lower():
                    dietary_terms.append('vegan')
                elif 'pescatarian' in restriction.lower():
                    dietary_terms.append('pescatarian')
                elif 'keto' in restriction.lower():
                    dietary_terms.append('keto')
                elif 'gluten' in restriction.lower():
                    dietary_terms.append('gluten-free')
                elif 'halal' in restriction.lower():
                    dietary_terms.append('halal')
                elif 'kosher' in restriction.lower():
                    dietary_terms.append('kosher')
        
        # Build health goal terms
        health_terms = []
        if user_prefs.get('health_goals'):
            if user_prefs['health_goals'].get('weight_loss'):
                health_terms.append('healthy')
            if user_prefs['health_goals'].get('muscle_gain'):
                health_terms.append('protein-rich')
        
        # Generate Query 1: Basic location + dietary
        dietary_str = ' '.join(dietary_terms) if dietary_terms else ''
        cuisine_str = cuisine if cuisine else 'restaurants'
        query1 = f"best {dietary_str} {cuisine_str} in {location}".strip()
        queries.append(query1)
        
        # Generate Query 2: Location + health focus
        health_str = ' '.join(health_terms) if health_terms else 'good'
        query2 = f"{health_str} restaurants {location} reviews".strip()
        queries.append(query2)
        
        # Generate Query 3: Platform-specific search
        platform_query = f"{location} restaurants"
        if dietary_terms:
            platform_query += f" {dietary_terms[0]}"
        platform_query += " zomato swiggy"
        queries.append(platform_query)
        
        logger.info(f"🔄 Generated {len(queries)} fallback queries: {queries}")
        return queries
    
    def _get_ai_nutrition_advice(self, query: str, user_prefs: Dict[str, Any]) -> str:
        """Get personalized nutrition advice using Mistral Agents API"""
        try:
            if not self.config.mistral_api_key:
                return "❌ Mistral API key not configured. Please set MISTRAL_API_KEY in your environment variables."
            
            # Build user context
            context_parts = []
            
            if user_prefs.get('age'):
                context_parts.append(f"Age: {user_prefs['age']}")
            if user_prefs.get('gender'):
                context_parts.append(f"Gender: {user_prefs['gender']}")
            if user_prefs.get('current_weight') and user_prefs.get('height_cm'):
                context_parts.append(f"Current weight: {user_prefs['current_weight']}kg, Height: {user_prefs['height_cm']}cm")
            if user_prefs.get('weight_goal'):
                context_parts.append(f"Weight goal: {user_prefs['weight_goal']}kg")
            if user_prefs.get('activity_level'):
                context_parts.append(f"Activity level: {user_prefs['activity_level']}")
            if user_prefs.get('daily_calorie_target'):
                context_parts.append(f"Daily calorie target: {user_prefs['daily_calorie_target']} calories")
            if user_prefs.get('dietary_restrictions'):
                restrictions = ', '.join(user_prefs['dietary_restrictions'])
                context_parts.append(f"Dietary restrictions: {restrictions}")
            if user_prefs.get('food_allergies'):
                allergies = ', '.join(user_prefs['food_allergies'])
                context_parts.append(f"Food allergies: {allergies}")
            if user_prefs.get('health_goals'):
                goals = [k.replace('_', ' ').title() for k, v in user_prefs['health_goals'].items() if v]
                if goals:
                    context_parts.append(f"Health goals: {', '.join(goals)}")
            
            # Create personalized prompt
            if context_parts:
                user_context = "User Profile: " + " | ".join(context_parts)
            else:
                user_context = "User Profile: No specific preferences provided"
            
            # Call Mistral Agents API
            headers = {
                "Authorization": f"Bearer {self.config.mistral_api_key}",
                "Content-Type": "application/json"
            }
            
            # Agents API payload structure
            payload = {
                "model": "mistral-large-latest",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert nutritionist and registered dietitian providing personalized, evidence-based nutrition advice. You have access to the user's complete profile and can provide comprehensive, tailored recommendations."
                    },
                    {
                        "role": "user",
                        "content": f"""Based on this user profile and question, provide comprehensive nutrition advice:

{user_context}

User Question: {query}

Provide detailed, personalized nutrition advice including:
1. Specific recommendations based on their goals and restrictions
2. Practical meal suggestions and food choices
3. Portion guidance and timing if relevant
4. Any special considerations for their dietary restrictions or health goals
5. Scientific rationale when appropriate

Keep the response helpful, actionable, and professional. Use emojis to make it engaging but maintain credibility."""
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.7,
                "top_p": 0.9,
                "stream": False
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",  # Agents API uses same endpoint but different payload structure
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                logger.info("✅ Generated personalized AI nutrition advice using Mistral Agents API")
                return ai_response
            else:
                error_msg = f"Mistral Agents API error: {response.status_code}"
                try:
                    error_detail = response.json()
                    if 'error' in error_detail:
                        error_msg += f" - {error_detail['error'].get('message', 'Unknown error')}"
                except:
                    error_msg += f" - {response.text[:100]}"
                
                logger.error(error_msg)
                
                if response.status_code == 401:
                    return f"❌ Authentication Error (401): Invalid Mistral API key. Please check your API key configuration."
                else:
                    return f"❌ API Error ({response.status_code}): {error_msg}"
                
        except Exception as e:
            logger.error(f"AI nutrition advice error: {e}")
            return f"❌ Error: {str(e)}"
    
    def generate_workout_plan(self, user_prefs: Dict[str, Any], query: str) -> str:
        """Generate personalized workout plan using Mistral Agents API - no fallbacks"""
        if not self.config.mistral_api_key:
            raise Exception("🔑 MISTRAL_API_KEY required for personalized workout plans. Please configure your API key.")
        
        # Build comprehensive user context
        context_parts = []
        if user_prefs.get('age'): 
            context_parts.append(f"Age: {user_prefs['age']} years")
        if user_prefs.get('gender'): 
            context_parts.append(f"Gender: {user_prefs['gender']}")
        if user_prefs.get('current_weight') and user_prefs.get('height_cm'):
            context_parts.append(f"Weight: {user_prefs['current_weight']}kg, Height: {user_prefs['height_cm']}cm")
        if user_prefs.get('activity_level'): 
            context_parts.append(f"Activity Level: {user_prefs['activity_level']}")
        if user_prefs.get('health_goals'): 
            goals = [k.replace('_', ' ').title() for k, v in user_prefs['health_goals'].items() if v]
            if goals:
                context_parts.append(f"Goals: {', '.join(goals)}")
        if user_prefs.get('dietary_restrictions'):
            context_parts.append(f"Diet: {', '.join(user_prefs['dietary_restrictions'])}")
        
        user_context = " | ".join(context_parts) if context_parts else "General fitness guidance needed"
        
        # Call Mistral Agents API
        headers = {
            "Authorization": f"Bearer {self.config.mistral_api_key}",
            "Content-Type": "application/json"
        }
        
        # Agents API payload structure
        payload = {
            "model": "mistral-large-latest",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert personal trainer and sports nutritionist providing evidence-based, personalized fitness and nutrition advice. You have access to comprehensive user profiles and can create detailed, tailored workout and nutrition plans."
                },
                {
                    "role": "user",
                    "content": f"""Create a comprehensive, personalized workout and nutrition plan based on this user profile and request:

User Profile: {user_context}
User Request: {query}

Provide a detailed plan including:

🏋️ **WORKOUT PLAN:**
- Specific exercises tailored to their fitness level and goals
- Sets, reps, and rest periods
- Weekly training frequency and schedule
- Progression plan for next 4-8 weeks

🍎 **NUTRITION TIMING:**  
- Pre-workout meal recommendations (timing and foods)
- Post-workout recovery nutrition
- Daily macro distribution based on their goals
- Hydration strategy

💪 **RECOVERY & PROGRESSION:**
- Rest day activities
- Sleep recommendations
- Signs of overtraining to watch for
- How to progress safely

Make it specific, actionable, and completely tailored to their profile. Include scientific rationale where helpful."""
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",  # Agents API uses same endpoint but different payload structure
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Mistral Agents API failed with status {response.status_code}: {response.text}")
        
        result = response.json()
        ai_response = result['choices'][0]['message']['content'].strip()
        logger.info("✅ Generated personalized workout plan using Mistral Agents API")
        return ai_response
    
    def search_restaurants(self, location: str, cuisine: str = "", user_id: str = None) -> Dict[str, Any]:
        """Search for restaurants using Exa API with personalized search based on user preferences"""
        try:
            if not self.config.exa_api_key:
                return {"error": "🔑 EXA_API_KEY not configured. Please set your Exa API key in environment variables to enable restaurant search."}
            
            logger.info(f"🔍 Starting restaurant search for '{location}' with cuisine '{cuisine}' for user '{user_id}'")
            
            headers = {
                "X-API-Key": self.config.exa_api_key,
                "Content-Type": "application/json"
            }
            
            # Get user preferences for personalized search
            user_prefs = {}
            if user_id:
                user_prefs = self.get_user_preferences(user_id)
                logger.info(f"📋 User preferences: {len(user_prefs)} items loaded")
            
            # Use preferred cuisine from user preferences if none specified
            if not cuisine and user_prefs.get('cuisine_preferences'):
                cuisine = user_prefs['cuisine_preferences'][0] if user_prefs['cuisine_preferences'] else ""
                logger.info(f"🍽️ Using preferred cuisine from profile: {cuisine}")
            
            # Generate AI-powered search queries
            search_queries = self._generate_smart_search_queries(location, user_prefs, cuisine)
            logger.info(f"🤖 AI generated {len(search_queries)} smart queries: {search_queries}")
            
            # Try multiple search strategies to get more comprehensive results
            all_results = []
            successful_queries = 0
            
            for i, query in enumerate(search_queries[:6], 1):  # Limit to 6 queries max
                try:
                    logger.info(f"Query {i}: '{query}'")
                    
                    payload = {
                        "query": query,
                        "type": "keyword",
                        "useAutoprompt": True,
                        "numResults": 4,
                        "contents": {
                            "text": True
                        },
                        "includeOrigin": ["zomato.com", "tripadvisor.com", "opentable.com", "yelp.com"]
                    }
                    
                    response = requests.post(
                        "https://api.exa.ai/search",
                        headers=headers,
                        json=payload,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])
                        all_results.extend(results)
                        successful_queries += 1
                        logger.info(f"✅ Query '{query}' found {len(results)} results")
                        
                        # If we have enough results, stop searching
                        if len(all_results) >= 10:
                            logger.info(f"🎯 Got enough results ({len(all_results)}), stopping search")
                            break
                    else:
                        logger.warning(f"❌ Query '{query}' failed: {response.status_code} - {response.text[:100]}")
                        
                except Exception as e:
                    logger.warning(f"❌ Query '{query}' exception: {str(e)}")
                    continue
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_results = []
            for result in all_results:
                url = result.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
            
            logger.info(f"🎯 Found {len(unique_results)} unique restaurant results for {location} from {successful_queries} successful queries")
            
            if not unique_results:
                logger.warning(f"⚠️ No results found for {location} after trying {len(search_queries)} queries")
                return {
                    "results": [],
                    "total_found": 0,
                    "debug_info": f"Tried {len(search_queries)} search queries, {successful_queries} successful API calls, but got 0 unique results"
                }
            
            return {
                "results": unique_results[:8],  # Return top 8 unique results
                "total_found": len(unique_results),
                "debug_info": f"Successfully found {len(unique_results)} restaurants using {successful_queries} successful queries"
            }
                
        except Exception as e:
            logger.error(f"❌ Restaurant search error: {e}")
            return {"error": f"Search failed: {str(e)}. Please check your EXA_API_KEY configuration."}
    
    def format_restaurant_results(self, search_results: Dict[str, Any], location: str, user_prefs: Dict[str, Any] = None) -> str:
        """Use Mistral AI to format restaurant search results with personalized recommendations"""
        try:
            # Handle errors
            if "error" in search_results:
                error_msg = search_results['error']
                if "EXA_API_KEY" in error_msg:
                    return f"🔑 **Restaurant Search Not Available**\n\n{error_msg}\n\n**To enable real-time restaurant search:**\n1. Get an API key from https://exa.ai\n2. Add `EXA_API_KEY=your_key_here` to your .env file\n3. Restart the application\n\n**Meanwhile, here are dining tips for {location}:**\n• Check Zomato, Google Maps, or TripAdvisor for reviews\n• Look for restaurants with healthy menu options\n• Consider the cooking methods - grilled, baked, or steamed are better choices"
                else:
                    return f"⚠️ **Search Issue:** {error_msg}\n\n**General dining tips for {location}:**\n• Look for restaurants with good reviews on Google Maps or Zomato\n• Check for healthy options like grilled proteins and fresh vegetables\n• Consider the cooking methods - grilled, baked, or steamed are better choices\n• Watch portion sizes and consider sharing dishes"
            
            results = search_results.get("results", [])
            total_found = search_results.get("total_found", len(results))
            debug_info = search_results.get("debug_info", "")
            
            if not results:
                debug_msg = f"\n\n🔍 **Debug Info:** {debug_info}" if debug_info else ""
                return f"🤔 **No Restaurant Results Found**\n\nI searched extensively but couldn't find specific restaurant recommendations for **{location}** right now. This could be due to:\n\n• **Location specificity**: Try a broader area (e.g., 'Mumbai' instead of 'Bandra West')\n• **Search timing**: Restaurant databases might be updating\n• **API limitations**: Some regions have limited coverage\n\n**Meanwhile, here are proven ways to find great restaurants:**\n• 🔍 **Zomato/Swiggy**: Best for Indian locations with reviews and ratings\n• 🗺️ **Google Maps**: Search 'restaurants near [location]' with photos and reviews\n• ✈️ **TripAdvisor**: Great for tourist areas and popular spots\n• 👥 **Ask locals**: Social media groups or friends in the area{debug_msg}"
            
            # Use Mistral AI to generate a conversational response
            return self._generate_ai_restaurant_recommendations(results, location, user_prefs)
            
        except Exception as e:
            logger.error(f"Error formatting results: {e}")
            return f"Found some restaurants for {location}, but had trouble formatting the results. Try searching on Zomato or Google Maps for local recommendations!"
    
    def _generate_ai_restaurant_recommendations(self, results: List[Dict], location: str, user_prefs: Dict[str, Any] = None) -> str:
        """Use Mistral Agents API to generate conversational restaurant recommendations"""
        try:
            if not self.config.mistral_api_key:
                # Fallback to simple formatting if no AI available
                response = f"🍽️ **Found {len(results)} restaurant recommendations for {location}:**\n\n"
                for i, result in enumerate(results[:5], 1):
                    title = result.get("title", "Restaurant")
                    url = result.get("url", "")
                    response += f"{i}. **{title}**\n{url}\n\n"
                return response
            
            # Build user context for personalization
            context_parts = []
            if user_prefs:
                if user_prefs.get('dietary_restrictions'):
                    dietary_list = ', '.join(user_prefs['dietary_restrictions'])
                    context_parts.append(f"Dietary restrictions: {dietary_list}")
                if user_prefs.get('food_allergies'):
                    allergy_list = ', '.join(user_prefs['food_allergies'])
                    context_parts.append(f"Food allergies: {allergy_list}")
                if user_prefs.get('health_goals'):
                    goals = [k.replace('_', ' ').title() for k, v in user_prefs['health_goals'].items() if v]
                    if goals:
                        context_parts.append(f"Health goals: {', '.join(goals)}")
            
            user_context = " | ".join(context_parts) if context_parts else "No specific dietary preferences"
            
            # Prepare restaurant data for AI
            restaurant_data = []
            for i, result in enumerate(results[:8], 1):  # Use up to 8 results
                title = result.get("title", f"Restaurant {i}")
                url = result.get("url", "")
                text = result.get("text", "")
                
                # Clean up text snippet
                clean_text = text.replace('\n', ' ').replace('\r', ' ') if text else ""
                snippet = clean_text[:200] + "..." if len(clean_text) > 200 else clean_text
                
                restaurant_info = f"{i}. {title}"
                if url:
                    restaurant_info += f" ({url})"
                if snippet:
                    restaurant_info += f" - {snippet}"
                
                restaurant_data.append(restaurant_info)
            
            restaurant_list = "\n".join(restaurant_data)
            
            # Call Mistral Agents API
            headers = {
                "Authorization": f"Bearer {self.config.mistral_api_key}",
                "Content-Type": "application/json"
            }
            
            # Agents API payload structure
            payload = {
                "model": "mistral-large-latest",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a knowledgeable food critic and nutrition expert providing personalized restaurant recommendations. You have expertise in dietary restrictions, health goals, and can provide actionable dining advice."
                    },
                    {
                        "role": "user",
                        "content": f"""Provide personalized restaurant recommendations based on this information:

User Profile: {user_context}
Location: {location}
Number of restaurants found: {len(results)}

Restaurant Search Results:
{restaurant_list}

Please provide a conversational, helpful response that includes:

1. **Welcome greeting** mentioning the location and number of restaurants found
2. **Top 3-5 restaurant recommendations** from the list above with:
   - Restaurant name as a clickable link if URL is available
   - Brief description of what makes it special
   - Why it matches the user's dietary needs/preferences
3. **Personalized dining tips** based on their dietary restrictions and health goals
4. **Healthy ordering suggestions** specific to their preferences
5. **Practical advice** like checking menus online, making reservations, etc.

Make the response warm, engaging, and actionable. Use emojis to make it visually appealing but keep it professional. Focus on how each recommendation aligns with their specific dietary needs and health goals.

Format the response in markdown with clear sections and bullet points for easy reading."""
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.7,
                "top_p": 0.9,
                "stream": False
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",  # Agents API uses same endpoint but different payload structure
                headers=headers,
                json=payload,
                timeout=25
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                logger.info("✅ Generated AI restaurant recommendations using Mistral Agents API")
                return ai_response
            else:
                logger.warning(f"⚠️ Mistral Agents API failed with status {response.status_code}, using fallback formatting")
                # Fallback to simple list
                response = f"🍽️ **Found {len(results)} great restaurant options in {location}:**\n\n"
                for i, result in enumerate(results[:5], 1):
                    title = result.get("title", "Restaurant")
                    url = result.get("url", "")
                    response += f"{i}. **{title}**\n"
                    if url:
                        response += f"🔗 {url}\n"
                    response += "\n"
                return response
                
        except Exception as e:
            logger.error(f"Error generating AI recommendations: {e}")
            # Simple fallback
            response = f"🍽️ **Found {len(results)} restaurants in {location}:**\n\n"
            for i, result in enumerate(results[:5], 1):
                title = result.get("title", "Restaurant")
                response += f"{i}. {title}\n"
            return response
    
    def detect_restaurant_query(self, query: str) -> Optional[str]:
        """Detect if the query is asking for restaurant recommendations and extract location"""
        query_lower = query.lower()
        restaurant_keywords = ['restaurant', 'dining', 'eat out', 'dinner', 'lunch', 'breakfast', 'food place', 'cafe', 'eatery', 'bar', 'bistro', 'dine', 'meal']
        food_keywords = ['serving', 'food', 'cuisine', 'dish', 'fish', 'chicken', 'vegetarian', 'vegan', 'italian', 'chinese', 'indian', 'pizza', 'burger', 'sushi', 'seafood']
        location_indicators = ['in ', 'at ', 'near ', 'around ', 'for ', 'at ']
        
        # Check for explicit restaurant keywords OR food + location patterns
        has_restaurant_keyword = any(keyword in query_lower for keyword in restaurant_keywords)
        has_food_location_pattern = (
            any(food_word in query_lower for food_word in food_keywords) and
            any(place in query_lower for place in ['pune', 'mumbai', 'delhi', 'bangalore', 'hyderabad', 'chennai', 'kolkata', 'gurgaon', 'noida', 'bandra', 'andheri', 'powai'])
        )
        
        if has_restaurant_keyword or has_food_location_pattern:
            logger.info(f"🍽️ Restaurant query detected: '{query}'")
            
            # Try to extract location using multiple strategies
            location = None
            
            # Strategy 1: Look for location indicators
            for indicator in location_indicators:
                if indicator in query_lower:
                    parts = query_lower.split(indicator)
                    if len(parts) > 1:
                        # Extract location after the indicator
                        location_words = []
                        remaining_text = parts[1].strip()
                        words = remaining_text.split()
                        
                        # Take words that look like location names (capitalized or known places)
                        for word in words[:4]:  # Check up to 4 words
                            clean_word = word.strip('.,!?')
                            if clean_word and (clean_word.istitle() or len(clean_word) > 3):
                                location_words.append(clean_word)
                            else:
                                break  # Stop at first non-location word
                        
                        if location_words:
                            location = ' '.join(location_words).title()
                            logger.info(f"📍 Extracted location using indicator '{indicator}': '{location}'")
                            break
            
            # Strategy 2: Check for common city/area names
            if not location:
                common_places = [
                    'pune', 'mumbai', 'delhi', 'bangalore', 'hyderabad', 'chennai', 'kolkata', 'gurgaon', 'noida',
                    'bandra', 'andheri', 'powai', 'koregaon park', 'viman nagar', 'whitefield', 'indiranagar',
                    'connaught place', 'karol bagh', 'cyber city', 'sector 29', 'mg road', 'brigade road'
                ]
                
                for place in common_places:
                    if place in query_lower:
                        location = place.title()
                        logger.info(f"📍 Found location from common places: '{location}'")
                        break
            
            # Strategy 3: Extract any capitalized words that might be locations
            if not location:
                import re
                # Look for sequences of capitalized words
                matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
                if matches:
                    # Take the longest match as it's likely a place name
                    location = max(matches, key=len)
                    logger.info(f"📍 Extracted location from capitalized words: '{location}'")
            
            return location
        
        return None
    
    def process_nutrition_query(self, query: str, user_id: str = None) -> str:
        """Process nutrition-related queries with AI-powered personalized recommendations"""
        try:
            if not self.validate_input(query):
                return "Invalid input. Please provide a valid nutrition question."
            
            # Get user preferences for personalized responses
            user_prefs = {}
            if user_id:
                user_prefs = self.get_user_preferences(user_id)
            
            # Check if this is a food logging request
            if self._is_food_logging_request(query):
                logger.info(f"Food logging request detected: {query[:50]}...")
                return self._handle_food_logging_request(query, user_id, user_prefs)
            
            # Check if this is a restaurant search query
            location = self.detect_restaurant_query(query)
            if location:
                logger.info(f"Restaurant query detected for location: {location}")
                search_results = self.search_restaurants(location, user_id=user_id)
                return self.format_restaurant_results(search_results, location, user_prefs)
            
            # Route queries to appropriate AI-powered handlers
            query_lower = query.lower()
            
            # Workout/fitness queries get dedicated workout plan generation
            if any(word in query_lower for word in ['workout', 'exercise', 'fitness', 'training', 'gym', 'strength', 'cardio', 'muscle']):
                logger.info(f"Processing workout query with dedicated AI trainer: {query[:50]}...")
                return self.generate_workout_plan(user_prefs, query)
            
            # All other nutrition queries use general AI nutrition advice
            logger.info(f"Processing nutrition query with AI nutritionist: {query[:50]}...")
            return self._get_ai_nutrition_advice(query, user_prefs)
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"⚠️ Sorry, I encountered an error processing your query: {str(e)}"
    
    def _is_food_logging_request(self, query: str) -> bool:
        """Detect if the query is a food logging request"""
        query_lower = query.lower()
        
        # Keywords that indicate food logging
        food_logging_keywords = [
            'ate', 'eaten', 'consumed', 'had', 'drank', 'drank',
            'log food', 'log meal', 'log calories', 'track food', 'track meal',
            'add food', 'add meal', 'record food', 'record meal',
            'just ate', 'just had', 'just consumed',
            'breakfast', 'lunch', 'dinner', 'snack', 'meal'
        ]
        
        # Check if query contains food logging keywords
        return any(keyword in query_lower for keyword in food_logging_keywords)
    
    def _handle_food_logging_request(self, query: str, user_id: str, user_prefs: Dict[str, Any]) -> str:
        """Handle food logging requests using AI to extract food information"""
        try:
            if not user_id:
                return "❌ Please set your User ID first to log food. Go to '🎯 Set Preferences' to set your User ID."
            
            # Use AI to extract food information from natural language
            headers = {
                "Authorization": f"Bearer {self.config.mistral_api_key}",
                "Content-Type": "application/json"
            }
            
            # Agents API payload for food extraction
            payload = {
                "model": "mistral-large-latest",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a nutrition expert that extracts food information from natural language. Extract the food item name and estimated calories. Return ONLY a JSON object with 'food_item' and 'calories' fields. If calories cannot be estimated, use 0."
                    },
                    {
                        "role": "user",
                        "content": f"""Extract food information from this text: "{query}"

Return ONLY a JSON object like this:
{{"food_item": "food name", "calories": estimated_calories}}

Examples:
- "I ate an apple" → {{"food_item": "apple", "calories": 95}}
- "Had grilled chicken breast" → {{"food_item": "grilled chicken breast", "calories": 165}}
- "Drank a glass of milk" → {{"food_item": "milk", "calories": 150}}
- "Just had coffee" → {{"food_item": "coffee", "calories": 5}}

If multiple foods, combine them: "ate apple and banana" → {{"food_item": "apple and banana", "calories": 200}}"""
                    }
                ],
                "max_tokens": 100,
                "temperature": 0.1,
                "top_p": 0.9,
                "stream": False
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                # Try to parse JSON response
                try:
                    import json
                    food_data = json.loads(ai_response)
                    food_item = food_data.get('food_item', 'Unknown food')
                    calories = food_data.get('calories', 0)
                    
                    # Log the food
                    log_result = self.log_food_intake(user_id, food_item, calories)
                    
                    # Create response message
                    response_msg = f"✅ {log_result}"
                    
                    # Add calorie target progress if available
                    if user_prefs.get('daily_calorie_target'):
                        target = user_prefs['daily_calorie_target']
                        response_msg += f"\n📊 Progress: Added {calories} calories toward your {target} calorie target."
                    
                    # Add nutrition tips based on user preferences
                    if user_prefs.get('dietary_restrictions') or user_prefs.get('health_goals'):
                        response_msg += f"\n💡 Tip: Keep up the great work tracking your nutrition!"
                    
                    logger.info(f"✅ Successfully logged food via chat: {food_item} ({calories} cal)")
                    return response_msg
                    
                except json.JSONDecodeError:
                    # Fallback: try to extract basic info
                    logger.warning(f"⚠️ AI response not valid JSON: {ai_response}")
                    return f"❌ I couldn't understand the food details. Please try: 'I ate [food name]' or 'Had [food name]'"
            
            else:
                logger.warning(f"⚠️ AI food extraction failed: {response.status_code}")
                return f"❌ I couldn't process your food logging request. Please try: 'I ate [food name]' or 'Had [food name]'"
                
        except Exception as e:
            logger.error(f"Error handling food logging request: {e}")
            return f"❌ Error logging food: {str(e)}"
    
    def log_food_intake(self, user_id: str, food_item: str, calories: float) -> str:
        """Log food intake to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO nutrition_logs (user_id, food_item, calories) VALUES (?, ?, ?)",
                    (user_id, food_item, calories)
                )
                conn.commit()
            return f"Logged: {food_item} ({calories} calories)"
        except Exception as e:
            logger.error(f"Error logging food: {e}")
            return f"Error logging food: {str(e)}"

def create_streamlit_interface(assistant: NutrisenseAssistant):
    """Create Streamlit interface with all features"""
    
    # Page configuration
    st.set_page_config(
        page_title="Nutrisense Nutrition Assistant",
        page_icon="🥗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    .status-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header
    st.markdown('<h1 class="main-header">🥗 Nutrisense Nutrition & Fitness Assistant</h1>', unsafe_allow_html=True)
    st.markdown("Get personalized nutrition advice based on your preferences, dietary restrictions, and health goals!")
    
    # System status
    try:
        exa_status = "✅ Connected" if assistant.config.exa_api_key else "⚠️ Not configured"
        mistral_status = "✅ Connected" if assistant.config.mistral_api_key else "⚠️ Not configured"
        db_status = "✅ Ready" if assistant.db_path.exists() else "⚠️ Initializing"
        
        st.markdown(f"""
        <div class="status-box">
            <strong>System Status:</strong><br>
            🍽️ Restaurant Search: {exa_status}<br>
            🤖 Smart Queries: {mistral_status}<br>
            💾 Database: {db_status}
        </div>
        """, unsafe_allow_html=True)
    except Exception as status_error:
        st.markdown("""
        <div class="warning-box">
            <strong>System Status:</strong> ⚠️ Checking system health...
        </div>
        """, unsafe_allow_html=True)
    
    # Sidebar for navigation
    st.sidebar.title("📱 Navigation")
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["🎯 Set Preferences", "💬 Nutrition Chat", "🍎 Food Logger"]
    )
    
    # Initialize session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = "demo_user"
    
    # Page routing
    if page == "🎯 Set Preferences":
        show_preferences_page(assistant)
    elif page == "💬 Nutrition Chat":
        show_chat_page(assistant)
    elif page == "🍎 Food Logger":
        show_food_logger_page(assistant)

def show_preferences_page(assistant: NutrisenseAssistant):
    """Show the user preferences page"""
    st.markdown('<h2 class="sub-header">🎯 Set Your Preferences</h2>', unsafe_allow_html=True)
    
    # User Identity Section
    st.markdown("### 🆔 User Identity")
    st.info("👆 **IMPORTANT:** Set your unique User ID first! This will save all your preferences and allow personalized AI advice.")
    
    user_id = st.text_input(
        "🆔 Your Unique User ID",
        value=st.session_state.user_id,
        placeholder="e.g., john_doe, sarah123, or your_name",
        help="💡 This identifies you in the system. Use the same ID each time to access your saved preferences!"
    )
    
    if user_id:
        st.session_state.user_id = user_id
    
    # Personal Information Section
    st.markdown("### 👤 Personal Information")
    col1, col2 = st.columns(2)
    
    with col1:
        age = st.number_input("Age", min_value=13, max_value=100, value=25)
        gender = st.selectbox("Gender", ["", "Male", "Female", "Other"])
        current_weight = st.number_input("Current Weight (kg)", min_value=30.0, max_value=300.0, value=70.0)
    
    with col2:
        target_weight = st.number_input("Target Weight (kg)", min_value=30.0, max_value=300.0, value=65.0)
        height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=170.0)
        activity_level = st.selectbox(
            "Activity Level",
            ["", "Sedentary", "Light", "Moderate", "Active", "Very Active"]
        )
    
    # Dietary Preferences Section
    st.markdown("### 🍽️ Dietary Preferences")
    
    dietary_restrictions = st.multiselect(
        "Dietary Restrictions/Preferences",
        ["Vegetarian", "Vegan", "Pescatarian", "Non-Vegetarian", "Gluten-Free", "Dairy-Free", "Keto", "Paleo", "Low-Carb", "Mediterranean", "Halal", "Kosher"]
    )
    
    food_allergies = st.multiselect(
        "Food Allergies",
        ["Nuts", "Shellfish", "Eggs", "Dairy", "Soy", "Fish", "Wheat/Gluten", "Sesame"]
    )
    
    cuisine_preferences = st.multiselect(
        "Favorite Cuisines",
        ["Italian", "Chinese", "Indian", "Mexican", "Mediterranean", "Japanese", "Thai", "American"]
    )
    
    # Health Goals Section
    st.markdown("### 🎯 Health Goals")
    
    col1, col2 = st.columns(2)
    with col1:
        daily_calories = st.number_input("Daily Calorie Target", min_value=1000, max_value=4000, value=2000)
        protein_target = st.number_input("Protein Target (g)", min_value=20.0, max_value=300.0, value=150.0)
    
    with col2:
        carb_target = st.number_input("Carb Target (g)", min_value=20.0, max_value=500.0, value=200.0)
        fat_target = st.number_input("Fat Target (g)", min_value=20.0, max_value=200.0, value=65.0)
    
    health_goals = st.multiselect(
        "Primary Health Goals",
        ["Weight Loss", "Weight Gain", "Muscle Gain", "General Health", "Athletic Performance"]
    )
    
    # Save button
    if st.button("💾 Save My Preferences", type="primary", use_container_width=True):
        if not user_id or not user_id.strip():
            st.error("❌ Please enter a valid User ID")
        else:
            try:
                preferences = {
                    'age': age,
                    'gender': gender,
                    'current_weight': current_weight,
                    'weight_goal': target_weight,
                    'height_cm': height,
                    'activity_level': activity_level,
                    'dietary_restrictions': dietary_restrictions,
                    'food_allergies': food_allergies,
                    'cuisine_preferences': cuisine_preferences,
                    'daily_calorie_target': int(daily_calories) if daily_calories else None,
                    'protein_target': protein_target,
                    'carb_target': carb_target,
                    'fat_target': fat_target,
                    'health_goals': {goal.lower().replace(' ', '_'): True for goal in health_goals}
                }
                
                result = assistant.save_user_preferences(user_id.strip(), preferences)
                st.markdown(f"""
                <div class="success-box">
                    {result}
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"❌ Error saving preferences: {str(e)}")

def show_chat_page(assistant: NutrisenseAssistant):
    """Show the nutrition chat page"""
    st.markdown('<h2 class="sub-header">💬 Nutrition Chat</h2>', unsafe_allow_html=True)
    
    # User ID for chat
    st.markdown("### 🆔 Your Identity")
    user_id_chat = st.text_input(
        "🆔 User ID",
        value=st.session_state.user_id,
        placeholder="Enter your user ID (same as in preferences)",
        help="⚠️ Use the same User ID as in preferences to get personalized AI advice!"
    )
    
    if user_id_chat:
        st.session_state.user_id = user_id_chat
    
    # Chat interface
    st.markdown("### 🤖 AI Nutrition Assistant")
    
    # Info box about food logging
    if user_id_chat:
        st.info("💡 **Pro Tip:** You can log food directly in chat! Try saying: 'I ate an apple', 'Had grilled chicken for lunch', or 'Just drank a coffee'")
    
    # Display chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me about nutrition, calories, fitness, or restaurants..."):
        # Add user message to chat
        st.chat_message("user").write(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Get AI response
        with st.spinner("🤖 Thinking..."):
            try:
                # Get user preferences for context
                user_prefs = assistant.get_user_preferences(user_id_chat) if user_id_chat else {}
                
                # Add context note if user has preferences
                context_note = ""
                if user_prefs and len(st.session_state.chat_history) > 1:
                    pref_summary = []
                    if user_prefs.get('dietary_restrictions'):
                        pref_summary.append(f"Dietary: {', '.join(user_prefs['dietary_restrictions'][:2])}")
                    if user_prefs.get('health_goals'):
                        goals = [k.replace('_', ' ').title() for k, v in user_prefs['health_goals'].items() if v]
                        if goals:
                            pref_summary.append(f"Goals: {', '.join(goals[:2])}")
                    
                    if pref_summary:
                        context_note = f"*Using your preferences: {' | '.join(pref_summary)}*\n\n"
                
                response = assistant.process_nutrition_query(prompt, user_id_chat)
                full_response = context_note + response
                
                # Add assistant response to chat
                st.chat_message("assistant").write(full_response)
                st.session_state.chat_history.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.chat_message("assistant").write(error_msg)
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History", type="secondary"):
        st.session_state.chat_history = []
        st.rerun()

def show_food_logger_page(assistant: NutrisenseAssistant):
    """Show the food logger page"""
    st.markdown('<h2 class="sub-header">🍎 Food Logger</h2>', unsafe_allow_html=True)
    st.markdown("Log your meals and snacks to track calories and monitor your nutrition goals!")
    
    # User ID for food logging
    user_id_food = st.text_input(
        "User ID",
        value=st.session_state.user_id,
        placeholder="Enter your user ID"
    )
    
    # Food logging form
    with st.form("food_log_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            food_item = st.text_input("Food Item", placeholder="e.g., Apple, Grilled Chicken Breast, Brown Rice")
            calories = st.number_input("Calories", min_value=0, value=0, placeholder="Enter calories")
            protein = st.number_input("Protein (g)", min_value=0.0, value=0.0, placeholder="Optional")
        
        with col2:
            carbs = st.number_input("Carbs (g)", min_value=0.0, value=0.0, placeholder="Optional")
            fat = st.number_input("Fat (g)", min_value=0.0, value=0.0, placeholder="Optional")
            meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"])
        
        submitted = st.form_submit_button("🍽️ Log Food", type="primary", use_container_width=True)
        
        if submitted:
            if not food_item or not calories:
                st.error("❌ Please enter both food item and calories.")
            else:
                try:
                    # Log to database
                    result = assistant.log_food_intake(user_id_food, food_item, calories)
                    
                    # Get user preferences for context
                    user_prefs = assistant.get_user_preferences(user_id_food)
                    
                    # Calculate daily progress if user has targets
                    progress_info = ""
                    if user_prefs.get('daily_calorie_target'):
                        target = user_prefs['daily_calorie_target']
                        progress_info = f"\n📊 Progress: Added {calories} calories toward your {target} calorie target."
                        
                        # Add macro breakdown if provided
                        if protein or carbs or fat:
                            macro_info = []
                            if protein:
                                macro_info.append(f"Protein: {protein}g")
                            if carbs:
                                macro_info.append(f"Carbs: {carbs}g")
                            if fat:
                                macro_info.append(f"Fat: {fat}g")
                            progress_info += f"\n🥗 Macros: {', '.join(macro_info)}"
                    
                    st.success(f"✅ {result}\n🕐 Meal: {meal_type}{progress_info}")
                    
                except Exception as e:
                    st.error(f"❌ Error logging food: {str(e)}")
    
    # View daily summary
    if st.button("📈 View Today's Log", type="secondary", use_container_width=True):
        try:
            with sqlite3.connect(assistant.db_path) as conn:
                cursor = conn.execute("""
                    SELECT food_item, calories, timestamp 
                    FROM nutrition_logs 
                    WHERE user_id = ? AND date(timestamp) = date('now')
                    ORDER BY timestamp DESC
                """, (user_id_food,))
                
                entries = cursor.fetchall()
                
                if not entries:
                    st.info("📝 No food entries logged today. Start tracking your meals!")
                else:
                    total_calories = sum(entry[1] for entry in entries)
                    
                    st.markdown(f"### 📊 Today's Food Log Summary")
                    st.metric("🔥 Total Calories", total_calories)
                    st.metric("📱 Meals Logged", len(entries))
                    
                    st.markdown("**Recent Entries:**")
                    for i, (food, cals, timestamp) in enumerate(entries[:5], 1):
                        time_str = timestamp.split()[1][:5] if ' ' in timestamp else 'Unknown'
                        st.write(f"{i}. {food} - {cals} cal ({time_str})")
                    
                    if len(entries) > 5:
                        st.write(f"... and {len(entries) - 5} more entries")
                    
                    # Show progress toward goal if user has target
                    user_prefs = assistant.get_user_preferences(user_id_food)
                    if user_prefs.get('daily_calorie_target'):
                        target = user_prefs['daily_calorie_target']
                        percentage = round((total_calories / target) * 100, 1)
                        st.progress(min(percentage / 100, 1.0))
                        st.write(f"🎯 **Goal Progress:** {percentage}% of {target} calorie target")
                        
        except Exception as e:
            st.error(f"❌ Error retrieving daily summary: {str(e)}")

def main():
    """Main function with comprehensive error handling"""
    try:
        logger.info("🚀 Starting Nutrisense Nutrition AI with Streamlit...")
        
        # Load configuration
        config = Config.from_env()
        
        # Make all APIs optional for faster startup
        if not config.exa_api_key:
            logger.info("EXA_API_KEY not configured - restaurant search will use fallback")
        
        if not config.mistral_api_key:
            logger.info("MISTRAL_API_KEY not configured - will use basic responses")
        
        logger.info("Starting with minimal dependencies for faster deployment")
        
        # Initialize assistant with error handling
        try:
            assistant = NutrisenseAssistant(config)
            logger.info("Assistant initialized successfully")
        except Exception as init_error:
            logger.error(f"Assistant initialization failed: {init_error}")
            # Create a minimal assistant for fallback
            assistant = NutrisenseAssistant(config)
        
        # Create and launch Streamlit interface
        create_streamlit_interface(assistant)
        
    except Exception as e:
        logger.error(f"Application startup error: {e}")
        st.error(f"❌ Error starting application: {e}")
        st.info("Please check your API keys and dependencies.")

if __name__ == "__main__":
    main() 