import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ArchitectureMap from './components/ArchitectureMap';
import InfoPanel from './components/InfoPanel';
import { PROPOSAL, NODES, EDGES } from './constants';
import { NodePosition } from './types';
import { analyzeArchitecture } from './services/geminiService';
import ApprovalPage from './pages/ApprovalPage';
import { useProgressStream } from './hooks/useProgressStream';

const ArchitectureViz: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeTicketKey, setActiveTicketKey] = useState<string | null>(null);
  
  // Connect to real-time progress stream
  const { tickets, connected } = useProgressStream();
  
  // Update active step based on real-time progress
  useEffect(() => {
    const ticketKeys = Object.keys(tickets);
    if (ticketKeys.length > 0) {
      // Use the most recently updated ticket (including completed ones)
      const mostRecent = ticketKeys.sort((a, b) => 
        tickets[b].updated_at - tickets[a].updated_at
      )[0];
      
      const ticket = tickets[mostRecent];
      setActiveTicketKey(mostRecent);
      
      // Map backend phases to frontend steps
      // Backend phases: 1=AI Analysis, 2=RAG, 3=Tavily, 4=Code Gen, 5=Validation, 6=Reflection, 7=Jira
      // Frontend steps: 0=idle, 1-7=workflow steps
      
      // If ticket is completed, show final phase (7)
      if (ticket.status === 'COMPLETED') {
        setActiveStep(7);
        console.log(`✅ Ticket completed: ${mostRecent}, showing final phase`);
      } else {
        setActiveStep(ticket.current_phase);
        console.log(`📊 Active ticket: ${mostRecent}, Phase: ${ticket.current_phase}`);
      }
    } else {
      // No tickets yet
      if (connected && activeStep === 0) {
        console.log('🔗 Connected but no tickets yet');
      }
    }
  }, [tickets, connected, activeStep]);
  
  const handleStartSimulation = () => {
    // Manual simulation fallback (when no webhook)
    setActiveStep(1);
    
    // Simulate progression
    let step = 1;
    const interval = setInterval(() => {
      step++;
      if (step > PROPOSAL.workflow_steps.length) {
        clearInterval(interval);
        setTimeout(() => setActiveStep(0), 2000);
      } else {
        setActiveStep(step);
      }
    }, 3000);
  };

  const handleReset = () => {
    setActiveStep(0);
    setSelectedNodeId(null);
    setActiveTicketKey(null);
  };

  const handleAnalyze = async (type: 'summary' | 'bottleneck' | 'security') => {
    setIsAnalyzing(true);
    setAiAnalysis(null);
    const result = await analyzeArchitecture(type);
    setAiAnalysis(result);
    setIsAnalyzing(false);
  };

  const currentStepData = PROPOSAL.workflow_steps.find(s => s.step_id === activeStep);
  const selectedNodeData = NODES.find(n => n.id === selectedNodeId) || null;

  return (
    <div className="min-h-screen flex flex-col bg-dark text-slate-200 overflow-hidden">
      {/* Header */}
      <header className="h-16 border-b border-slate-700 bg-slate-900/80 backdrop-blur-md flex items-center justify-between px-6 z-20">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center font-bold text-white shadow-lg">
            H
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-white">{PROPOSAL.project_name}</h1>
            <div className="flex space-x-2 text-[10px] uppercase text-slate-500 tracking-wider">
              {PROPOSAL.category_focus.map((cat, i) => (
                <span key={i} className="bg-slate-800 px-1 rounded">{cat}</span>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Connection Status */}
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-xs text-slate-400">
              {connected ? 'Live' : 'Offline'}
            </span>
          </div>
          
          {/* Active Ticket Badge */}
          {activeTicketKey && (
            <div className="px-3 py-1 bg-blue-600/20 border border-blue-500/30 rounded-md text-xs text-blue-300 font-mono">
              {activeTicketKey}
            </div>
          )}
          
          <div className="flex space-x-2">
            {activeStep === 0 && (
              <button 
                onClick={handleStartSimulation}
                className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md text-sm font-semibold transition-colors shadow-[0_0_15px_rgba(37,99,235,0.5)] flex items-center"
              >
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Test Simulation
              </button>
            )}
            {activeStep > 0 && (
              <button 
                onClick={handleReset}
                className="border border-slate-600 hover:bg-slate-800 text-slate-300 px-4 py-2 rounded-md text-sm transition-colors"
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Diagram */}
        <div className="flex-1 relative bg-slate-950 p-8 flex flex-col">
           {/* Analysis Overlay */}
           {aiAnalysis && (
            <div className="absolute top-6 left-6 right-6 z-30 bg-slate-800/95 backdrop-blur border border-purple-500/50 p-6 rounded-xl shadow-2xl max-w-2xl mx-auto animate-in fade-in slide-in-from-top-4">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-purple-400 font-bold uppercase tracking-wider text-sm flex items-center">
                  <span className="w-2 h-2 bg-purple-500 rounded-full mr-2 animate-pulse"></span>
                  Gemini Architect Analysis
                </h3>
                <button onClick={() => setAiAnalysis(null)} className="text-slate-500 hover:text-white">✕</button>
              </div>
              <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-line">{aiAnalysis}</p>
            </div>
          )}

          <div className="flex-1 w-full max-w-5xl mx-auto h-full min-h-[500px]">
             <ArchitectureMap 
               nodes={NODES} 
               edges={EDGES} 
               activeStep={activeStep}
               onNodeClick={(node) => setSelectedNodeId(node.id)}
               selectedNodeId={selectedNodeId}
             />
          </div>

          {/* AI Controls Bar */}
          <div className="h-16 mt-4 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between px-4">
             <span className="text-xs text-slate-500 font-mono">POWERED BY GEMINI 2.5 FLASH</span>
             <div className="flex space-x-2">
                <button 
                  disabled={isAnalyzing}
                  onClick={() => handleAnalyze('summary')}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded border border-slate-700 disabled:opacity-50"
                >
                  {isAnalyzing ? '...' : 'Exec Summary'}
                </button>
                <button 
                  disabled={isAnalyzing}
                  onClick={() => handleAnalyze('bottleneck')}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-orange-400 rounded border border-slate-700 disabled:opacity-50"
                >
                   {isAnalyzing ? '...' : 'Find Bottlenecks'}
                </button>
                <button 
                  disabled={isAnalyzing}
                  onClick={() => handleAnalyze('security')}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-red-400 rounded border border-slate-700 disabled:opacity-50"
                >
                   {isAnalyzing ? '...' : 'Security Check'}
                </button>
             </div>
          </div>
        </div>

        {/* Right: Info Panel */}
        <div className="w-96 flex-shrink-0 z-10 shadow-2xl">
          <InfoPanel 
            selectedNode={selectedNodeData} 
            proposal={PROPOSAL}
            activeStep={activeStep}
            currentStepDescription={currentStepData?.details || ''}
          />
        </div>
      </div>
    </div>
  );
};

// Main App with Router
const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ArchitectureViz />} />
        <Route path="/approve/:sessionId" element={<ApprovalPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;