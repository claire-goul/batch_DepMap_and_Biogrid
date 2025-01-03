import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Upload } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const API_URL = 'https://batch-depmap-and-biogrid.onrender.com';

const GeneNetworkVisualizer = () => {
  const [networkData, setNetworkData] = useState(null);
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [serverStatus, setServerStatus] = useState(null);
  const [debugInfo, setDebugInfo] = useState(null);

  useEffect(() => {
    checkServerStatus();
  }, []);

  const checkServerStatus = async () => {
    try {
      console.log('Checking server status...');
      const response = await fetch(`${API_URL}/status/`);
      if (!response.ok) throw new Error('Server status check failed');
      const status = await response.json();
      console.log('Server status:', status);
      setServerStatus(status);
    } catch (err) {
      console.error('Server status error:', err);
      setError('Could not connect to server: ' + err.message);
    }
  };

  const processFile = async (file) => {
    if (!file) {
      setError('Please upload a genes file');
      return;
    }

    console.log('Processing file:', file.name);
    setIsProcessing(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('genes_file', file);

      const response = await fetch(`${API_URL}/upload/`, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json',
        },
        mode: 'cors',
        credentials: 'omit'
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Server response:', errorText);
        throw new Error(errorText || 'Network processing failed');
      }

      const data = await response.json();
      console.log('Received network data:', data);

      // Process edges and create debug info
      const biogridEdges = data.edges.filter(e => e.isBiogrid === true);
      const correlationEdges = data.edges.filter(e => !e.isBiogrid);
      
      const debugStats = {
        totalEdges: data.edges.length,
        biogridEdges: biogridEdges.length,
        correlationEdges: correlationEdges.length,
        sampleBiogrid: biogridEdges.slice(0, 3),
        sampleCorrelation: correlationEdges.slice(0, 3)
      };

      console.log('Debug statistics:', debugStats);
      setDebugInfo(debugStats);
      setNetworkData(data);

    } catch (err) {
      console.error('Processing error:', err);
      setError(`Error processing file: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto m-4">
      <CardHeader>
        <CardTitle>Gene Network Visualizer</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {serverStatus ? (
            <div className="space-y-2">
              <Alert variant={serverStatus.links_file_loaded ? "default" : "destructive"}>
                <AlertDescription>
                  Links file: {serverStatus.links_file_loaded ? 
                    `Loaded (${serverStatus.links_file_rows.toLocaleString()} rows)` : 
                    "Not loaded"}
                </AlertDescription>
              </Alert>
              <Alert variant={serverStatus.biogrid_file_loaded ? "default" : "destructive"}>
                <AlertDescription>
                  BioGrid file: {serverStatus.biogrid_file_loaded ? 
                    `Loaded (${serverStatus.biogrid_file_rows.toLocaleString()} rows)` : 
                    "Not loaded"}
                </AlertDescription>
              </Alert>
            </div>
          ) : (
            <Alert variant="destructive">
              <AlertDescription>
                Checking server status...
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              <h3 className="text-sm font-medium">Upload Genes of Interest File (.xlsx)</h3>
            </div>
            <Input
              type="file"
              accept=".xlsx"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  processFile(e.target.files[0]);
                }
              }}
              className="cursor-pointer"
              disabled={isProcessing}
            />
            {isProcessing && (
              <div className="text-sm text-gray-500">Processing file...</div>
            )}
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {debugInfo && (
            <Alert>
              <AlertDescription>
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-gray-100 p-2 rounded">
                      <div className="font-medium">Total Edges</div>
                      <div className="text-lg">{debugInfo.totalEdges}</div>
                    </div>
                    <div className="bg-red-50 p-2 rounded">
                      <div className="font-medium">BioGrid Edges</div>
                      <div className="text-lg">{debugInfo.biogridEdges}</div>
                    </div>
                    <div className="bg-blue-50 p-2 rounded">
                      <div className="font-medium">Correlation Edges</div>
                      <div className="text-lg">{debugInfo.correlationEdges}</div>
                    </div>
                  </div>

                  {debugInfo.sampleBiogrid.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2">Sample BioGrid Edges:</h4>
                      {debugInfo.sampleBiogrid.map((edge, i) => (
                        <div key={i} className="text-sm bg-red-50 p-2 mb-1 rounded">
                          {edge.source} → {edge.target}
                        </div>
                      ))}
                    </div>
                  )}

                  {debugInfo.sampleCorrelation.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2">Sample Correlation Edges:</h4>
                      {debugInfo.sampleCorrelation.map((edge, i) => (
                        <div key={i} className="text-sm bg-blue-50 p-2 mb-1 rounded">
                          {edge.source} → {edge.target} (Score: {edge.value.toFixed(3)})
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          )}

          {networkData && networkData.nodes.length > 0 && (
            <div className="border rounded-lg bg-white p-4">
              <div className="flex flex-wrap gap-4 text-sm">
                <div className="flex items-center">
                  <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                  <span>Genes of Interest ({networkData.nodes.filter(n => n.isInterest).length})</span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-3 rounded-full bg-gray-400 mr-2"></div>
                  <span>Other Genes ({networkData.nodes.filter(n => !n.isInterest).length})</span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-1 bg-gray-400 mr-2"></div>
                  <span>Correlation Edge ({debugInfo?.correlationEdges || 0})</span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-1 bg-red-500 mr-2"></div>
                  <span>BioGrid Edge ({debugInfo?.biogridEdges || 0})</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default GeneNetworkVisualizer;
