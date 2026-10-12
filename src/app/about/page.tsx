'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Brain,
  Cpu,
  Database,
  FlaskConical,
  ArrowLeft,
  BarChart3,
  Sparkles,
  Layers,
} from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import { getToken, getUser } from '@/lib/api';
import clsx from 'clsx';

const mlModels = [
  {
    name: 'TabTransformer',
    type: 'Deep Learning (Transformer)',
    accuracy: '85.9%',
    auc: '0.970',
    params: '22 categorical + 7 numerical features',
    embed_dim: 64,
    layers: '3× Transformer blocks',
    file: 'tabular_best.pt',
  },
  {
    name: 'XGBoost',
    type: 'Gradient Boosted Trees',
    accuracy: '84.5%',
    auc: '0.962',
    params: 'All 30 tabular features',
    estimators: 200,
    max_depth: 8,
    file: 'xgboost_best.json',
  },
  {
    name: 'Random Forest',
    type: 'Ensemble of Decision Trees',
    accuracy: '81.3%',
    auc: '0.953',
    params: 'All 30 tabular features',
    estimators: 300,
    max_depth: 12,
    file: 'randomforest_best.pkl',
  },
];

const llmInfo = {
  provider: 'OpenRouter (API)',
  model: 'Qwen 2.5 72B Instruct (via OpenRouter)',
  endpoint: 'https://openrouter.ai/api/v1',
  temperature: 0.3,
  maxTokens: 512,
  purpose:
    'Generates clinical summaries and actionable recommendations based on prediction results and patient profile.',
};

const architecture = [
  { layer: 'Frontend', tech: 'Next.js 14, Tailwind CSS, Recharts', icon: Layers },
  { layer: 'Backend', tech: 'FastAPI, Motor (async MongoDB)', icon: Database },
  { layer: 'ML Engine', tech: 'PyTorch TabTransformer (tabular_best.pt)', icon: Brain },
  { layer: 'LLM Service', tech: 'OpenRouter API + Qwen 2.5 72B', icon: Sparkles },
  { layer: 'Database', tech: 'MongoDB Atlas (cloud)', icon: Cpu },
];

export default function AboutPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ email: string; role: string } | null>(
    null
  );

  useEffect(() => {
    if (!getToken()) {
      router.replace('/login');
      return;
    }
    const u = getUser();
    if (u) setUser(u);
  }, [router]);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#F5F1DC] dark:bg-[#121212]">
      <Sidebar />

      <div className="lg:pl-64 transition-all duration-300">
        {/* Top bar */}
        <header className="bg-white dark:bg-neutral-900 border-b-2 border-black dark:border-neutral-600 shadow-soft">
          <div className="px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/dashboard')}
                className="h-8 w-8 rounded-[4px] bg-white dark:bg-neutral-800 border-2 border-black dark:border-neutral-600 flex items-center justify-center text-neutral-600 dark:text-neutral-300 shadow-[2px_2px_0_#111111] dark:shadow-[2px_2px_0_#3F3F46] hover:bg-neutral-100 dark:hover:bg-neutral-700 hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none transition-smooth"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
              <div>
                <h1 className="text-lg font-semibold text-gray-800 dark:text-neutral-50">About</h1>
                <p className="text-xs text-gray-400 dark:text-neutral-400">
                  System architecture & model information
                </p>
              </div>
            </div>
            <div className="h-8 w-8 rounded-[3px] bg-black flex items-center justify-center text-white text-sm font-semibold shadow-soft">
              {user.email.charAt(0).toUpperCase()}
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8 space-y-8">
          {/* ML Models Section */}
          <section>
            <div className="flex items-center gap-3 mb-5">
              <div className="h-8 w-8 rounded-[4px] border-2 border-black bg-brand-50 dark:bg-brand-950/30 flex items-center justify-center">
                <Brain className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              </div>
              <div>
                  <h2 className="text-base font-semibold text-gray-800 dark:text-neutral-50">
                  Machine Learning Models
                </h2>
                <p className="text-xs text-gray-400 dark:text-neutral-400">
                  Three-class classification: Easy / Moderate / Difficult
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {mlModels.map((model) => (
                <div
                  key={model.name}
                  className="bg-white dark:bg-neutral-900 rounded-[4px] shadow-card border-2 border-black dark:border-neutral-600 p-5 card-gradient hover:shadow-lg transition-smooth"
                >
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-neutral-50">
                      {model.name}
                    </h3>
                    <span className="text-[10px] font-semibold text-neutral-700 dark:text-neutral-200 uppercase tracking-wider bg-gray-100 dark:bg-neutral-800 border-2 border-black dark:border-neutral-600 px-2 py-0.5 rounded-[3px]">
                      {model.type.split(' ')[0]}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-neutral-300 mb-4">{model.type}</p>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500 dark:text-neutral-300">Accuracy</span>
                      <span className="text-sm font-bold text-brand-600 dark:text-brand-400">
                        {model.accuracy}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">AUC-ROC</span>
                      <span className="text-sm font-bold text-success-600">
                        {model.auc}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Features</span>
                      <span className="text-xs font-medium text-gray-700 dark:text-neutral-200 text-right">
                        {model.params}
                      </span>
                    </div>
                  </div>

                  <div className="mt-3 pt-3 border-t-2 border-black dark:border-neutral-600 text-[10px] text-gray-400 dark:text-neutral-400 font-mono">
                    {model.file}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* LLM Section */}
          <section>
            <div className="flex items-center gap-3 mb-5">
              <div className="h-8 w-8 rounded-[4px] border-2 border-black bg-brand-50 dark:bg-brand-950/30 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              </div>
              <div>
                  <h2 className="text-base font-semibold text-gray-800 dark:text-neutral-50">
                  LLM Assistant
                </h2>
                <p className="text-xs text-gray-400 dark:text-neutral-400">
                  AI-powered clinical decision support
                </p>
              </div>
            </div>

            <div className="bg-white dark:bg-neutral-900 rounded-[4px] shadow-card border-2 border-black dark:border-neutral-600 p-5 card-gradient">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-gray-400 dark:text-neutral-300 mb-1">Provider</p>
                  <p className="text-sm font-semibold text-gray-800 dark:text-neutral-50">
                    {llmInfo.provider}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 dark:text-neutral-300 mb-1">Model</p>
                  <p className="text-sm font-semibold text-gray-800 dark:text-neutral-50 font-mono">
                    {llmInfo.model}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 dark:text-neutral-300 mb-1">Temperature</p>
                  <p className="text-sm font-semibold text-gray-800 dark:text-neutral-50">
                    {llmInfo.temperature}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 dark:text-neutral-300 mb-1">Max Tokens</p>
                  <p className="text-sm font-semibold text-gray-800 dark:text-neutral-50">
                    {llmInfo.maxTokens}
                  </p>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t-2 border-black dark:border-neutral-600">
                <p className="text-xs text-gray-400 dark:text-neutral-300 mb-1">Purpose</p>
                <p className="text-sm text-gray-700 dark:text-neutral-200">{llmInfo.purpose}</p>
              </div>
            </div>
          </section>

          {/* Architecture Section */}
          <section>
            <div className="flex items-center gap-3 mb-5">
              <div className="h-8 w-8 rounded-[4px] bg-gray-100 border-2 border-black flex items-center justify-center">
                <Layers className="h-4 w-4 text-gray-600" />
              </div>
              <div>
                  <h2 className="text-base font-semibold text-gray-800 dark:text-neutral-50">
                  System Architecture
                </h2>
                <p className="text-xs text-gray-400 dark:text-neutral-400">
                  End-to-end technology stack
                </p>
              </div>
            </div>

            <div className="bg-white dark:bg-neutral-900 rounded-[4px] shadow-card border-2 border-black dark:border-neutral-600 divide-y-2 divide-black/15 dark:divide-neutral-700">
              {architecture.map((layer, i) => {
                const Icon = layer.icon;
                return (
                  <div
                    key={layer.layer}
                    className="flex items-center gap-4 px-5 py-4"
                  >
                    <div
                      className={clsx(
                        'h-8 w-8 rounded-[4px] border-2 border-black flex items-center justify-center',
                        i === 0
                           ? 'bg-brand-50 text-brand-600 dark:bg-brand-950/30 dark:text-brand-400'
                           : i === 1
                           ? 'bg-green-50 text-green-600'
                           : i === 2
                           ? 'bg-brand-50 text-brand-600 dark:bg-brand-950/30 dark:text-brand-400'
                          : i === 3
                          ? 'bg-amber-50 text-amber-600'
                          : 'bg-blue-50 text-blue-600'
                      )}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 dark:text-neutral-50">
                        {layer.layer}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-neutral-300">{layer.tech}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
