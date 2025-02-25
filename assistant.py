import openai
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# OpenAI API Key (Ensure it's set in your environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Ensure this is set in Render's environment variables
import os
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Product FAQ Database
def get_product_info(question):
    product_faqs = {
        "What is the price for 10 bags?": "Great choice! The price for 10 bags is $28.80 per bag. Plus, if your order exceeds $100, you qualify for free shipping! 😊",
        "Do you offer free shipping?": "Yes! We offer free shipping on orders over $100. Let me know if I can assist with anything else. 😊",
        "What are the shipping times?": "Shipping usually takes 5-7 business days, depending on your location. Need help with anything else?"
    }
    return product_faqs.get(question, None)

# Logging System
def log_interaction(agent, step, data):
    with open(f"{agent}_logs.txt", "a") as file:
        file.write(f"[{step}] {data}\n")

# Supervisor Agent - Verifies Accuracy & Language Style
def supervisor_agent(response, query):
    """Ensures accuracy of product data and improves human-like tone."""
    check_prompt = f"Verify the accuracy of this response: '{response}'. Ensure all product pricing and shipping details are correct based on the known data. If incorrect, provide the correct response."
    
    correction = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a meticulous fact-checking AI. Ensure all details are accurate."},
            {"role": "user", "content": check_prompt}
        ]
    ).choices[0].message.content.strip()
    
    style_prompt = f"Adjust this response to be more natural and human-like: '{correction}'. Ensure it sounds warm, engaging, and clear."
    
    refined_response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI that enhances text to be more engaging and human-like."},
            {"role": "user", "content": style_prompt}
        ]
    ).choices[0].message.content.strip()
    
    log_interaction("Supervisor", "Checked & Refined", f"Query: {query}\nOriginal: {response}\nCorrected: {correction}\nRefined: {refined_response}")
    return refined_response

# Pre-sale Support Assistant - Handles Customer Inquiry
def pre_sale_support_assistant(query):
    """Retrieves product information, composes responses, and performs a self-check."""
    product_answer = get_product_info(query)
    if product_answer:
        log_interaction("PreSaleSupport", "Product Info", f"Query: {query} -> Response: {product_answer}")
        return product_answer  # Return stored answer if available
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful pre-sale assistant. Answer customer queries about products, pricing, and discounts."},
            {"role": "user", "content": query}
        ]
    ).choices[0].message.content.strip()
    
    log_interaction("PreSaleSupport", "Generated Response", f"Query: {query} -> Response: {response}")
    return supervisor_agent(response, query)  # Hand off to Supervisor

# Output - Final Delivery to Customer
def output_response(query, response):
    """Outputs the final response after Supervisor check."""
    log_interaction("Output", "Final Response", f"Query: {query} -> Response: {response}")
    return response

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "Invalid request. 'question' field is required."}), 400
    
    user_query = data["question"]
    response = pre_sale_support_assistant(user_query)  # Assistant + Supervisor Processing
    final_output = output_response(user_query, response)  # Output Final Response
    
    return jsonify({"response": final_output})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port)

