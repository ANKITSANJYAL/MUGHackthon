import React from 'react';
import { NodePosition, ProposalData } from '../types';

interface InfoPanelProps {
  selectedNode: NodePosition | null;
  proposal: ProposalData;
  activeStep: number;
  currentStepDescription: string;
}

const InfoPanel: React.FC<InfoPanelProps> = ({ selectedNode, proposal, activeStep, currentStepDescription }) => {
  return (
    <div className="h-full bg-slate-900 border-l border-slate-700 p-6 overflow-y-auto flex flex-col font-light text-slate-300">
      
      {/* Simulation Status */}
      <div className="mb-8 p-4 bg-slate-800 rounded-lg border border-slate-700 shadow-inner">
        <h3 className="text-xs uppercase tracking-widest text-slate-500 mb-2">System Status</h3>
        <div className="flex items-center space-x-3 mb-2">
          <div className={`w-3 h-3 rounded-full ${activeStep > 0 ? 'bg-green-500 animate-pulse' : 'bg-slate-600'}`}></div>
          <span className="font-mono text-lg text-white">
            {activeStep === 0 ? 'IDLE' : `STEP 0${activeStep}`}
          </span>
        </div>
        <p className="text-sm text-slate-400 h-16 overflow-y-auto">
          {activeStep === 0 ? 'Waiting for trigger...' : currentStepDescription}
        </p>
      </div>

      {/* Selected Node Details */}
      {selectedNode ? (
        <div className="animate-in slide-in-from-right fade-in duration-300">
          <div className="flex items-center space-x-3 mb-4">
            <span className="text-4xl">{selectedNode.icon}</span>
            <h2 className="text-2xl font-bold text-white">{selectedNode.label}</h2>
          </div>
          
          <div className="space-y-6">
            <div>
              <h4 className="text-xs uppercase text-slate-500 mb-1">Role</h4>
              <p className="text-sm border-b border-slate-700 pb-2">{selectedNode.description}</p>
            </div>

            {selectedNode.tech && (
              <>
                <div>
                  <h4 className="text-xs uppercase text-slate-500 mb-1">Technology</h4>
                  <p className="text-white font-semibold">{selectedNode.tech.name || selectedNode.tech.purpose}</p>
                </div>

                {selectedNode.tech.libraries && (
                  <div>
                    <h4 className="text-xs uppercase text-slate-500 mb-1">Libraries/Stack</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedNode.tech.libraries.map(lib => (
                        <span key={lib} className="px-2 py-1 bg-slate-800 text-cyan-400 text-xs rounded border border-slate-700">
                          {lib}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <h4 className="text-xs uppercase text-slate-500 mb-1">Purpose</h4>
                  <p className="text-sm bg-slate-800/50 p-3 rounded italic border-l-2 border-purple-500">
                    "{selectedNode.tech.purpose}"
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-600">
          <svg className="w-16 h-16 mb-4 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
          </svg>
          <p>Select a node to inspect architecture details.</p>
        </div>
      )}

      {/* Cost Estimate Footer */}
      <div className="mt-auto pt-6 border-t border-slate-700">
        <h4 className="text-xs uppercase text-slate-500 mb-2">Estimated Cost</h4>
        <div className="flex justify-between items-center bg-slate-800 p-3 rounded">
          <span className="text-sm text-slate-400">POC Total</span>
          <span className="text-green-400 font-mono font-bold">{proposal.estimated_cost.total_estimated_poc_cost}</span>
        </div>
      </div>
    </div>
  );
};

export default InfoPanel;
