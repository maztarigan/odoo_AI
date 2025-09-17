# odoo_AI

Custom module collection for Odoo 14.0.

## model_ai

The `model_ai` addon provides a simple interface to send prompts to OpenAI's
ChatGPT API directly from Odoo and store the responses.

### Configuration

1. Install the module via the Apps menu.
2. Navigate to *Settings → Technical → Parameters → System Parameters*.
3. Create or update the parameter `model_ai.openai_api_key` with your OpenAI
   API key.

### Usage

Open the **Model AI → Prompts** menu, write a new prompt, and click **Send
Prompt** to fetch the response from ChatGPT.
