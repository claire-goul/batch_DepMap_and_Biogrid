import React, { useState, useEffect } from 'react';
import Graph from 'react-graph-vis';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Input } from './ui/input';
import { Alert, AlertDescription } from './ui/alert';

const API_URL = 'https://batch-depmap-and-biogrid.onrender.com';

const GeneNetworkVisualizer = () => {
  const [networkData, setNetworkData] = useState(null);
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [serverStatus, setServerStatus] = useState(null);

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

      // Convert data to vis-network format
      const nodes = data.nodes.map(node => ({
        id: node.id,
        label: node.id,
        color: node.isInterest ? '#22c55e' : '#94a3b8',
        size: 20
      }));

      const edges = data.edges.map((edge, index) => ({
        id: index,
        from: edge.source,
        to: edge.target,
        color: edge.isBiogrid ? '#9333ea' : (edge.value >= 0 ? '#22c55e' : '#ef4444'),
        width: edge.isBiogrid ? 1 : Math.abs(edge.value) * 2,
      }));

      setNetworkData({ nodes, edges });

    } catch (err) {
      console.error('Processing error:', err);
      setError(`Error processing file: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const options = {
    nodes: {
      shape: 'dot',
      size: 16,
      font: {
        size: 12
      },
      borderWidth: 1,
      borderWidthSelected: 2
    },
    edges: {
      smooth: {
        type: 'continuous'
      }
    },
    physics: {
      stabilization: {
        iterations: 100
      },
      barnesHut: {
        gravitationalConstant: -2000,
        centralGravity: 0.3,
        springLength: 95,
        springConstant: 0.04,
        damping: 0.09
      }
    },
    interaction: {
      hover: true,
      zoomView: true,
      dragView: true,
      multiselect: true
    },
    height: '500px'
  };

  const events = {
    select: function(event) {
      // Handler for node/edge selection
      console.log('Selected elements:', event);
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
            <div className="space-y-2 mb-4">
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
                      <div className="w-3 h-1 bg-green-500 mr-2"></div>
                      Positive Correlation
                    </div>
                    <div className="flex items-center">
                      <div className="w-3 h-1 bg-red-500 mr-2"></div>
                      Negative Correlation
                    </div>
                    <div className="flex items-center">
                      <div className="w-3 h-1 bg-purple-500 mr-2"></div>
                      BioGrid
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
