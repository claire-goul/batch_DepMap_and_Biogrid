import React, { useState, useEffect } from 'react';
import Graph from 'react-graph-vis';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';

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

      console.log('Sending request to:', `${API_URL}/upload/`);
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

      // Debug information about edges
      const debugStats = {
        totalEdges: data.edges.length,
        biogridEdges: data.edges.filter(e => e.isBiogrid).length,
        sampleEdges: data.edges.slice(0, 5).map(e => ({
          source: e.source,
          target: e.target,
          isBiogrid: e.isBiogrid,
          value: e.value
        }))
      };
      console.log('Edge statistics:', debugStats);
      setDebugInfo(debugStats);

      const nodes = data.nodes.map(node => ({
        id: node.id,
        label: node.id,
        color: node.isInterest ? '#22c55e' : '#94a3b8',
        size: node.isInterest ? 25 : 20,
        font: {
          size: node.isInterest ? 16 : 14,
          color: '#333333'
        },
        borderWidth: 0
      }));

      const edges = data.edges.map((edge, index) => {
        const hasCorrelation = typeof edge.value === 'number';
        const isBiogrid = Boolean(edge.isBiogrid); // Explicit boolean conversion
        
        console.log(`Processing edge ${index}:`, {
          from: edge.source,
          to: edge.target,
          isBiogrid: edge.isBiogrid,
          value: edge.value,
          convertedBiogrid: isBiogrid
        });
        
        return {
          id: index,
          from: edge.source,
          to: edge.target,
          color: {
            color: isBiogrid ? '#ef4444' : '#94a3b8',
            highlight: isBiogrid ? '#f87171' : '#cbd5e1',
            opacity: 0.8
          },
          width: isBiogrid ? 2 : (hasCorrelation ? Math.max(1, Math.abs(edge.value) * 3) : 1),
          smooth: false,
          arrows: {
            to: false,
            from: false
          }
        };
      });

      setNetworkData({ nodes, edges });

    } catch (err) {
      console.error('Processing error:', err);
      setError(`Error processing file: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // ... (keep existing options and events objects)

  return (
    <Card className="w-full max-w-4xl mx-auto m-4">
      <CardHeader>
        <CardTitle>Gene Network Visualizer</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* ... (keep existing server status alerts) */}

          <div>
            <h3 className="text-sm font-medium mb-2">Upload Genes of Interest File (.xlsx)</h3>
            <Input
              type="file"
              accept=".xlsx"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  processFile(e.target.files[0]);
                }
              }}
              className="flex-1 cursor-pointer"
              disabled={isProcessing}
            />
            {isProcessing && <div className="mt-2">Processing file...</div>}
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Add debug information display */}
          {debugInfo && (
            <Alert>
              <AlertDescription>
                <div className="space-y-2">
                  <p>Total Edges: {debugInfo.totalEdges}</p>
                  <p>BioGrid Edges: {debugInfo.biogridEdges}</p>
                  <div className="mt-2">
                    <p className="font-medium">Sample Edges:</p>
                    {debugInfo.sampleEdges.map((edge, i) => (
                      <div key={i} className="text-sm mt-1">
                        {edge.source} → {edge.target} 
                        (BioGrid: {String(edge.isBiogrid)}, 
                        Value: {edge.value})
                      </div>
                    ))}
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {networkData && (
            <div className="space-y-4">
              <div className="border rounded-lg overflow-hidden bg-white">
                <div style={{ height: '500px' }}>
                  <Graph
                    graph={networkData}
                    options={options}
                    events={events}
                  />
                </div>

                <div className="p-4 border-t">
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center">
                      <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                      Genes of Interest
                    </div>
                    <div className="flex items-center">
                      <div className="w-3 h-3 rounded-full bg-gray-400 mr-2"></div>
                      Other Genes
                    </div>
                    <div className="flex items-center">
                      <div className="w-3 h-1 bg-gray-400 mr-2"></div>
                      Correlation Edge
                    </div>
                    <div className="flex items-center">
                      <div className="w-3 h-1 bg-red-500 mr-2"></div>
                      BioGrid Edge
                    </div>
                  </div>
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
