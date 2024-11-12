export default async function (request, context) {
  const response = await context.next();
  
  // Add CORS headers
  const headers = new Headers(response.headers);
  headers.set('Access-Control-Allow-Origin', 'https://batchnetwork.netlify.app');
  headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  headers.set('Access-Control-Allow-Headers', '*');
  
  // Handle OPTIONS request
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers
    });
  }

  // Return response with new headers
  return new Response(response.body, {
    status: response.status,
    headers
  });
}
