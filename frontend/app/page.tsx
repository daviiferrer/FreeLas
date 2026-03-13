"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, Beaker, CheckCircle2, ChevronRight, FileText, Search, Settings2, Zap, CopyIcon, SaveIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { useSSE } from "@/hooks/use-sse";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

// API Base URL - update this for production if needed
const API_BASE = "http://localhost:8000/api";

// Types
interface Project {
  project_id: string;
  title: string;
  description: string;
  category: string;
  status: string;
  ai_score_phase1?: number;
  ai_complexity?: string;
  url: string;
  [key: string]: any;
}

interface Proposal extends Project {
  proposal_text: string;
  recommended_price?: string;
  recommended_delivery_time?: string;
  client_name?: string;
}

export default function DashboardPage() {
  const { events, isConnected, activeThinking } = useSSE(`${API_BASE}/events`);
  const [stats, setStats] = useState({ total: 0, new: 0, phase1_pass: 0, phase2_pass: 0, phase3_pass: 0, rejected: 0 });
  const [projects, setProjects] = useState<Project[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  
  const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(null);
  const [editProposalText, setEditProposalText] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch initial data
  const fetchData = async () => {
    try {
      const statsRes = await fetch(`${API_BASE}/stats`);
      setStats(await statsRes.json());

      const projRes = await fetch(`${API_BASE}/projects?limit=50`);
      setProjects((await projRes.json()).projects);

      const propRes = await fetch(`${API_BASE}/proposals?limit=50`);
      setProposals((await propRes.json()).proposals);
    } catch (e) {
      console.error("Failed to fetch data", e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const triggerPipeline = async () => {
    try {
      await fetch(`${API_BASE}/pipeline/run`, { method: "POST" });
    } catch (e) {
      console.error("Error triggering pipeline", e);
    }
  };

  const openProposalModal = (proposal: Proposal) => {
    setSelectedProposal(proposal);
    setEditProposalText(proposal.proposal_text || "");
    setIsModalOpen(true);
  };

  const saveProposal = async () => {
    if (!selectedProposal) return;
    try {
      await fetch(`${API_BASE}/proposals/${selectedProposal.project_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ proposal_text: editProposalText })
      });
      setIsModalOpen(false);
      fetchData();
    } catch (e) {
      console.error("Error saving proposal", e);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(editProposalText);
  };

  const thinkingAgents = Object.keys(activeThinking);

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-6 w-6 text-primary animate-pulse" />
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">
              FreeLaas
            </span>
            <Badge variant="outline" className="ml-2 font-mono text-xs">v1.1</Badge>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="relative flex h-3 w-3">
                {isConnected ? (
                  <>
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                  </>
                ) : (
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-destructive"></span>
                )}
              </span>
              <span className="text-muted-foreground font-mono hidden sm:inline">
                {isConnected ? "WS Connected" : "Disconnected"}
              </span>
            </div>
            <Button onClick={triggerPipeline} size="sm" className="gap-2 shadow-lg shadow-primary/20 transition-all hover:shadow-primary/40">
              <Activity className="h-4 w-4" />
              Executar Pipeline
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1 container py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Col: Live Feed & Thinking */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <Card className="flex-1 overflow-hidden border-border/50 shadow-sm flex flex-col h-[calc(100vh-12rem)]">
            <CardHeader className="py-4 border-b bg-muted/20">
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4 text-primary" /> 
                Terminal de Agentes
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 flex-1 flex flex-col overflow-hidden relative">
              
              {/* Thinking Panel overlay */}
              <AnimatePresence>
                {thinkingAgents.length > 0 && (
                  <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 20 }}
                    className="absolute z-10 bottom-0 left-0 right-0 p-4 pt-12 bg-gradient-to-t from-background via-background/95 to-transparent border-t"
                  >
                    {thinkingAgents.map(agent => (
                      <div key={agent} className="bg-muted/50 rounded-lg p-3 border border-border/50 text-sm mb-2 shadow-xl backdrop-blur-md">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-primary flex items-center gap-2">
                            <Beaker className="h-3 w-3 animate-bounce" /> {agent}
                          </span>
                          <span className="text-xs text-muted-foreground animate-pulse">pensando...</span>
                        </div>
                        <ScrollArea className="h-24 opacity-80 font-mono text-xs">
                          {activeThinking[agent]?.full_thinking || "..."}
                        </ScrollArea>
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Event Log */}
              <ScrollArea className="flex-1 p-4">
                <div className="flex flex-col gap-3 font-mono text-sm pb-32">
                  {events.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-48 text-muted-foreground opacity-50">
                      <Search className="h-8 w-8 mb-2 animate-pulse" />
                      <p>Aguardando telemetria...</p>
                    </div>
                  ) : (
                    events.map((ev, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`flex gap-3 items-start p-2 rounded-md ${i === 0 ? 'bg-primary/5 border border-primary/20' : ''}`}
                      >
                        <span className="text-xs text-muted-foreground shrink-0 mt-1">
                          {new Date().toLocaleTimeString('pt-BR', { hour12: false })}
                        </span>
                        <div className="flex-1 break-words">
                          {ev.message || JSON.stringify(ev)}
                        </div>
                      </motion.div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Right Col: Dashboard Tabs */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="bg-muted/10 border-border/50 shadow-sm">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <p className="text-sm font-medium text-muted-foreground">Scraping (Total)</p>
                <p className="text-3xl font-bold">{stats.total}</p>
              </CardContent>
            </Card>
            <Card className="bg-primary/5 border-primary/20 shadow-sm">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <p className="text-sm font-medium text-primary">Scanner (Qualif.)</p>
                <p className="text-3xl font-bold">{stats.phase1_pass}</p>
              </CardContent>
            </Card>
            <Card className="bg-accent/5 border-accent/20 shadow-sm">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <p className="text-sm font-medium text-accent">Analyst (Prep.)</p>
                <p className="text-3xl font-bold">{stats.phase2_pass}</p>
              </CardContent>
            </Card>
            <Card className="bg-emerald-500/10 border-emerald-500/30 shadow-sm">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <p className="text-sm font-medium text-emerald-500">Aprovados</p>
                <p className="text-3xl font-bold">{stats.phase3_pass}</p>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="proposals" className="flex-1 flex flex-col">
            <TabsList className="grid w-full grid-cols-3 max-w-md bg-muted/30">
              <TabsTrigger value="proposals">🎯 Propostas (Prontas)</TabsTrigger>
              <TabsTrigger value="qualified">✅ Qualificados</TabsTrigger>
              <TabsTrigger value="all">📁 Todos</TabsTrigger>
            </TabsList>

            <TabsContent value="proposals" className="flex-1 mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {proposals.length === 0 ? (
                  <div className="col-span-2 text-center py-12 text-muted-foreground border border-dashed rounded-lg">
                    Nenhuma proposta pronta ainda.
                  </div>
                ) : (
                  proposals.map(p => (
                    <Card key={p.project_id} className="flex flex-col h-full border-primary/20 shadow-sm hover:shadow-primary/10 transition-shadow">
                      <CardHeader className="pb-3">
                        <div className="flex justify-between items-start gap-2">
                          <CardTitle className="text-lg leading-tight line-clamp-2">{p.title}</CardTitle>
                          <Badge variant="default" className="shrink-0">{p.recommended_price || "Negociável"}</Badge>
                        </div>
                        <CardDescription className="flex items-center gap-2">
                          <span className="truncate">{p.client_name || "Cliente Oculto"}</span>
                          <span>•</span>
                          <span>{p.category}</span>
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="flex-1">
                        <p className="text-sm text-foreground/80 line-clamp-4 bg-muted/30 p-3 rounded-md italic">
                          "{p.proposal_text}"
                        </p>
                      </CardContent>
                      <CardFooter className="pt-3 border-t bg-muted/10 gap-2">
                        <Button className="w-full" onClick={() => openProposalModal(p)}>Ver e Enviar</Button>
                        <a 
                          href={p.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className={cn(buttonVariants({ variant: "outline", size: "icon" }))}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </a>
                      </CardFooter>
                    </Card>
                  ))
                )}
              </div>
            </TabsContent>

            <TabsContent value="qualified" className="mt-4">
              <div className="space-y-4">
                {projects.filter(p => ["phase1_pass", "phase2_pass"].includes(p.status)).length === 0 ? (
                   <div className="text-center py-12 text-muted-foreground border border-dashed rounded-lg">Nenhum projeto em qualificação no momento.</div>
                ) : (
                  projects.filter(p => ["phase1_pass", "phase2_pass"].includes(p.status)).map(p => (
                    <Card key={p.project_id} className="border-accent/20">
                       <CardHeader className="py-4">
                         <div className="flex justify-between items-center">
                            <div>
                              <CardTitle className="text-base">{p.title}</CardTitle>
                              <CardDescription className="text-xs mt-1">Score: {p.ai_score_phase1} | Fase: {p.status}</CardDescription>
                            </div>
                            <Badge variant="outline" className="text-accent border-accent/30">{p.ai_complexity || "Analisando..."}</Badge>
                         </div>
                       </CardHeader>
                    </Card>
                  ))
                )}
              </div>
            </TabsContent>

            <TabsContent value="all" className="mt-4">
               <div className="space-y-4">
                {projects.map(p => (
                  <Card key={p.project_id} className="opacity-80 hover:opacity-100 transition-opacity">
                      <CardHeader className="py-3">
                        <div className="flex justify-between items-center">
                          <CardTitle className="text-sm font-medium truncate">{p.title}</CardTitle>
                          <Badge variant="secondary" className="text-xs">{p.status}</Badge>
                        </div>
                      </CardHeader>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </main>

      {/* Proposal Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-[700px] gap-6">
          <DialogHeader>
            <DialogTitle>Ajustar Proposta</DialogTitle>
            <DialogDescription>
              Revise o texto gerado por IA antes de enviar para o cliente no 99Freelas.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4">
             <div className="flex gap-4 mb-2">
                <div className="flex-1 bg-muted p-3 rounded-md">
                  <span className="text-xs text-muted-foreground block mb-1">Preço Sugerido (IA)</span>
                  <span className="font-semibold text-primary">{selectedProposal?.recommended_price || "Não estimado"}</span>
                </div>
                <div className="flex-1 bg-muted p-3 rounded-md">
                  <span className="text-xs text-muted-foreground block mb-1">Prazo Sugerido (IA)</span>
                  <span className="font-semibold text-accent">{selectedProposal?.recommended_delivery_time || "Não estimado"}</span>
                </div>
             </div>
             <Textarea 
               value={editProposalText}
               onChange={(e) => setEditProposalText(e.target.value)}
               className="min-h-[250px] font-sans leading-relaxed resize-y"
             />
          </div>

          <DialogFooter className="gap-2 sm:justify-end border-t pt-4">
            <Button variant="outline" type="button" onClick={() => setIsModalOpen(false)}>
              Cancelar
            </Button>
            <Button variant="secondary" onClick={copyToClipboard} className="gap-2">
              <CopyIcon className="h-4 w-4" /> Copiar Texto
            </Button>
            <Button onClick={saveProposal} className="gap-2">
              <SaveIcon className="h-4 w-4" /> Salvar Edição
            </Button>
            <a 
              href={selectedProposal?.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className={cn(buttonVariants({ variant: "default" }), "gap-2 bg-emerald-600 hover:bg-emerald-700 text-white")}
            >
              Ir para Projeto 99Freelas <ChevronRight className="h-4 w-4" />
            </a>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
