
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}


Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { question, notebook_id, user_id } = await req.json();
    
    if (!question || !notebook_id) {
      throw new Error('question and notebook_id are required');
    }

    console.log('Querying notebook:', { notebook_id, question, user_id });

    // Reutiliza la lógica de send-chat-message
    const webhookUrl = Deno.env.get('NOTEBOOK_TECH_SUPPORT_URL');
    const authHeader = Deno.env.get('NOTEBOOK_GENERATION_AUTH');
    
    if (!webhookUrl || !authHeader) {
      throw new Error('Environment variables not set');
    }

    const webhookResponse = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader,
      },
      body: JSON.stringify({
        session_id: notebook_id,
        message: question,
        user_id: user_id || 'external-user',
        timestamp: new Date().toISOString()
      })
    });

    if (!webhookResponse.ok) {
      throw new Error(`Webhook error: ${webhookResponse.status}`);
    }

    const webhookData = await webhookResponse.json();

    return new Response(
      JSON.stringify({ success: true, response: webhookData }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error in query-notebook:', error);
    return new Response(
      JSON.stringify({ error: (error as Error).message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});