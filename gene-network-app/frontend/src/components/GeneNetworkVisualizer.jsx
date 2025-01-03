import React, { useState, useEffect } from 'react';
import { Upload } from 'lucide-react';
import Graph from 'react-graph-vis';

const API_URL = 'https://batch-depmap-and-biogrid.onrender.com';

const options = {
  nodes: {
    shape: 'dot',
    size: 20,
    borderWidth: 0,
    shadow: false,
    font: {
      size: 16,
      color: '#333333'
    }
  },
  edges: {
    width: 2,
    smooth: false,
    shadow: false,
    arrows: {
      to: false,
      from: false
    }
  },
  physics: {
    enabled: false,
    forceAtlas2Based: {
      gravitationalConstant: -50,
      centralGravity: 0.01,
      springLength: 100,
      springConstant: 0.08,
      damping: 0.4,
      avoidOverlap: 1.5
    },
    solver: 'forceAtlas2Based',
    stabilization: {
      enabled: true,
      iterations: 1000,
      updateInterval: 25,
      fit: true
    },
    adaptiveTimestep: true,
    timestep: 0.5,
    minVelocity: 0.75
  },
  layout: {
    improvedLayout: true,
    randomSeed: 42
  },
  interaction: {
    hover: true,
    zoomView: true,
    dragView: true,
    dragNodes: true,
    multiselect: true
  },
  height: '500px'
};

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

      // Process nodes and edges for visualization
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
        const isBiogrid = edge.isBiogrid === true;
        
        console.log(`Processing edge ${index}:`, {
          source: edge.source,
          target: edge.target,
          isBiogrid: edge.isBiogrid,
          value: edge.value
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

  const events = {
    select: function(event) {
      console.log('Selected elements:', event);
    }
  };

  return (
    <div className="max-w-4xl mx-auto m-4 bg-white rounded-lg shadow">
      <div className="p-6 border-b">
        <h2 className="text-2xl font-semibold">Gene Network Visualizer</h2>
      </div>

      <div className="p-6 space-y-4">
        {/* Server Status */}
        {serverStatus ? (
          <div className="space-y-2">
            <div className={`p-4 rounded ${serverStatus.links_file_loaded ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
              Links file: {serverStatus.links_file_loaded ? 
                `Loaded (${serverStatus.links_file_rows.toLocaleString()} rows)` : 
                "Not loaded"}
            </div>
            <div className={`p-4 rounded ${serverStatus.biogrid_file_loaded ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
              BioGrid file: {serverStatus.biogrid_file_loaded ? 
                `Loaded (${serverStatus.biogrid_file_rows.toLocaleString()} rows)` : 
                "Not loaded"}
            </div>
          </div>
        ) : (
          <div className="p-4 bg-yellow-50 text-yellow-800 rounded">
            Checking server status...
          </div>
        )}

        {/* File Upload */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Upload className="w-4 h-4" />
            <h3 className="text-sm font-medium">Upload Genes of Interest File (.xlsx)</h3>
          </div>
          <input
            type="file"
            accept=".xlsx"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                processFile(e.target.files[0]);
              }
            }}
            className="block w-full text-sm border border-gray-300 rounded cursor-pointer file:mr-4 file:py-2 file:px-4 file:border-0 file:text-sm file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
            disabled={isProcessing}
          />
          {isProcessing && (
            <div className="text-sm text-gray-500">Processing file...</div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-4 bg-red-50 text-red-800 rounded">
            {error}
          </div>
        )}

        {/* Debug Information */}
        {debugInfo && (
          <div className="p-4 bg-blue-50 rounded">
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white p-4 rounded shadow-sm">
                  <div className="font-medium">Total Edges</div>
                  <div className="text-lg">{debugInfo.totalEdges}</div>
                </div>
                <div className="bg-white p-4 rounded shadow-sm">
                  <div className="font-medium">BioGrid Edges</div>
                  <div className="text-lg text-red-600">{debugInfo.biogridEdges}</div>
                </div>
                <div className="bg-white p-4 rounded shadow-sm">
                  <div className="font-medium">Correlation Edges</div>
                  <div className="text-lg text-blue-600">{debugInfo.correlationEdges}</div>
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
          </div>
        )}

        {/* Network Visualization */}
        {networkData && networkData.nodes.length > 0 && (
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
                    <span>Genes of Interest ({networkData.nodes.filter(n => n.color === '#22c55e').length})</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-gray-400 mr-2"></div>
                    <span>Other Genes ({networkData.nodes.filter(n => n.color === '#94a3b8').length})</span>
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
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GeneNetworkVisualizer;
