import React, { useState, useRef, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Input } from './ui/input';
import { Alert, AlertDescription } from './ui/alert';
import { Button } from './ui/button';
import { ZoomIn, ZoomOut, Move } from 'lucide-react';
import ForceGraph2D from 'react-force-graph';

const API_URL = 'https://batch-depmap-and-biogrid.onrender.com';

const GeneNetworkVisualizer = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [serverStatus, setServerStatus] = useState(null);
  const graphRef = useRef();

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

      const networkData = await response.json();
      console.log('Received network data:', networkData);
      
      // Convert to ForceGraph format
      const graphData = {
        nodes: networkData.nodes.map(node => ({
          id: node.id,
          isInterest: node.isInterest,
          color: node.isInterest ? '#22c55e' : '#94a3b8'
        })),
        links: networkData.edges.map(edge => ({
          source: edge.source,
          target: edge.target,
          value: edge.value,
          isBiogrid: edge.isBiogrid,
          color: edge.isBiogrid ? '#9333ea' : (edge.value >= 0 ? '#22c55e' : '#ef4444')
        }))
      };

      setGraphData(graphData);

    } catch (err) {
      console.error('Processing error:', err);
      setError(`Error processing file: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleZoomIn = () => {
    const currentZoom = graphRef.current.zoom();
    graphRef.current.zoom(currentZoom * 1.2);
  };

  const handleZoomOut = () => {
    const currentZoom = graphRef.current.zoom();
    graphRef.current.zoom(currentZoom / 1.2);
  };

  const handleResetView = () => {
    graphRef.current.centerAt();
    graphRef.current.zoom(1);
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

          {graphData.nodes.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Button variant="outline" size="sm" onClick={handleZoomIn}>
                  <ZoomIn className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={handleZoomOut}>
                  <ZoomOut className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={handleResetView}>
                  Reset View
                </Button>
                <Move className="w-4 h-4 ml-2 text-gray-500" />
                <span className="text-sm text-gray-500">Drag to pan</span>
              </div>

              <div className="border rounded-lg overflow-hidden bg-white">
                <ForceGraph2D
                  ref={graphRef}
                  graphData={graphData}
                  nodeLabel="id"
                  nodeColor="color"
                  linkColor="color"
                  linkWidth={link => link.isBiogrid ? 1 : Math.abs(link.value) * 2}
                  linkOpacity={0.6}
                  nodeRelSize={6}
                  width={600}
                  height={500}
                  d3VelocityDecay={0.3}
                  cooldownTime={2000}
                />

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
