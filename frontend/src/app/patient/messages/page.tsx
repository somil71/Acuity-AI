'use client';
import { useEffect, useRef, useState } from 'react';
import useSWR from 'swr';
import { fetcher, getHeaders } from '@/api';
import { MessageSquare, Send, Plus, X, AlertCircle, Loader2 } from 'lucide-react';

const ALL_DOCTORS = [
  'DOC_CAR_1', 'DOC_CAR_2',
  'DOC_GEN_1', 'DOC_GEN_2',
  'DOC_ORT_1', 'DOC_ORT_2',
  'DOC_PED_1', 'DOC_PED_2',
];

interface Thread {
  thread_id: string;
  patient_id: string;
  doctor_id: string;
  subject: string;
  created_at: string;
  last_message_at: string;
}

interface Message {
  message_id: string;
  sender_id: string;
  sender_role: string;
  body: string;
  sent_at: string;
  is_read: boolean;
}

interface ThreadDetail {
  thread_id: string;
  subject: string;
  patient_id: string;
  doctor_id: string;
  messages: Message[];
}

export default function MessagesPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');
  const [sending, setSending] = useState(false);
  const [showNewModal, setShowNewModal] = useState(false);
  const [newDoctor, setNewDoctor] = useState(ALL_DOCTORS[0]);
  const [newSubject, setNewSubject] = useState('');
  const [newMessage, setNewMessage] = useState('');
  const [creatingThread, setCreatingThread] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setUserId(localStorage.getItem('userId'));
  }, []);

  const { data: threads, mutate: mutateThreads, error: threadsError, isLoading: threadsLoading } =
    useSWR<Thread[]>('/messages/threads', fetcher, { refreshInterval: 5000 });

  // Auto-select first thread
  useEffect(() => {
    if (threads && threads.length > 0 && !selectedId) {
      setSelectedId(threads[0].thread_id);
    }
  }, [threads, selectedId]);

  const { data: threadDetail, mutate: mutateDetail } = useSWR<ThreadDetail>(
    selectedId ? `/messages/threads/${selectedId}` : null,
    fetcher,
    { refreshInterval: 3000 }
  );

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [threadDetail?.messages]);

  const handleReply = async () => {
    if (!replyText.trim() || !selectedId) return;
    setSending(true);
    try {
      const res = await fetch(`http://localhost:8000/api/messages/threads/${selectedId}/reply`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ body: replyText.trim() }),
      });
      if (res.ok) {
        setReplyText('');
        mutateDetail();
        mutateThreads();
      }
    } finally {
      setSending(false);
    }
  };

  const handleCreateThread = async () => {
    if (!newSubject.trim() || !newMessage.trim()) return;
    setCreatingThread(true);
    try {
      const res = await fetch('http://localhost:8000/api/messages/threads', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          doctor_id: newDoctor,
          subject: newSubject.trim(),
          first_message: newMessage.trim(),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setShowNewModal(false);
        setNewSubject('');
        setNewMessage('');
        await mutateThreads();
        setSelectedId(data.thread_id);
      }
    } finally {
      setCreatingThread(false);
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Messages</h1>
          <p className="text-slate-500 text-sm mt-0.5">Communicate securely with your care team</p>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors shadow-sm shadow-blue-600/20"
        >
          <Plus size={16} />
          New Message
        </button>
      </div>

      {/* Main panel */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Thread List */}
        <aside className="w-72 shrink-0 bg-white rounded-2xl border border-slate-200 flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              {threads?.length ?? 0} Conversation{threads?.length !== 1 ? 's' : ''}
            </p>
          </div>

          {threadsLoading && (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 size={20} className="animate-spin text-slate-300" />
            </div>
          )}

          {!threadsLoading && (!threads || threads.length === 0) && (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-center">
              <MessageSquare size={32} className="text-slate-300" />
              <p className="text-sm text-slate-400">No conversations yet</p>
              <button
                onClick={() => setShowNewModal(true)}
                className="text-blue-600 text-xs font-semibold hover:underline"
              >
                Start one
              </button>
            </div>
          )}

          <ul className="flex-1 overflow-y-auto divide-y divide-slate-50">
            {threads?.map((t) => (
              <li key={t.thread_id}>
                <button
                  onClick={() => setSelectedId(t.thread_id)}
                  className={`w-full text-left px-4 py-3.5 hover:bg-slate-50 transition-colors ${
                    selectedId === t.thread_id
                      ? 'bg-blue-50 border-l-[3px] border-blue-500 pl-[13px]'
                      : ''
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-800 truncate">{t.subject}</p>
                  <p className="text-xs text-slate-500 mt-0.5">Dr. {t.doctor_id}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {new Date(t.last_message_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Thread Detail */}
        <div className="flex-1 bg-white rounded-2xl border border-slate-200 flex flex-col overflow-hidden min-w-0">
          {!selectedId ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center p-8">
              <div className="bg-slate-100 rounded-full p-5">
                <MessageSquare size={36} className="text-slate-400" />
              </div>
              <h3 className="font-bold text-slate-700">No conversation selected</h3>
              <p className="text-slate-500 text-sm max-w-xs">
                Select a conversation on the left or start a new message with your care team.
              </p>
            </div>
          ) : (
            <>
              {/* Thread header */}
              <div className="px-6 py-4 border-b border-slate-100 shrink-0 bg-slate-50/50">
                <h2 className="font-bold text-slate-800">
                  {threadDetail?.subject ?? '...'}
                </h2>
                {threadDetail?.doctor_id && (
                  <p className="text-xs text-slate-500 mt-0.5">Dr. {threadDetail.doctor_id}</p>
                )}
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                {!threadDetail && (
                  <div className="flex justify-center py-10">
                    <Loader2 size={24} className="animate-spin text-slate-300" />
                  </div>
                )}
                {threadDetail?.messages?.map((msg) => {
                  // Match by sender_id OR sender_role='patient'
                  const isOwnMessage =
                    msg.sender_id === userId || msg.sender_role === 'patient';
                  return (
                    <div
                      key={msg.message_id}
                      className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                          isOwnMessage
                            ? 'bg-blue-600 text-white rounded-br-sm'
                            : 'bg-slate-100 text-slate-800 rounded-bl-sm'
                        }`}
                      >
                        {!isOwnMessage && (
                          <p className="text-[10px] font-bold text-slate-500 mb-1 uppercase tracking-wide">
                            Dr. {msg.sender_id}
                          </p>
                        )}
                        <p>{msg.body}</p>
                        <p
                          className={`text-[11px] mt-1.5 ${
                            isOwnMessage ? 'text-blue-200' : 'text-slate-400'
                          }`}
                        >
                          {new Date(msg.sent_at).toLocaleTimeString([], { timeStyle: 'short' })}
                        </p>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Reply Box */}
              <div className="border-t border-slate-100 px-4 py-3 flex gap-3 shrink-0">
                <textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleReply();
                    }
                  }}
                  placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
                  rows={2}
                  className="flex-1 resize-none bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
                <button
                  onClick={handleReply}
                  disabled={sending || !replyText.trim()}
                  className="self-end flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors"
                >
                  {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                  Send
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* New Thread Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-800">New Message Thread</h2>
              <button
                onClick={() => setShowNewModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5">
                  Doctor
                </label>
                <select
                  value={newDoctor}
                  onChange={(e) => setNewDoctor(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
                  {ALL_DOCTORS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5">
                  Subject
                </label>
                <input
                  type="text"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  placeholder="e.g. Question about my medication"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5">
                  Message
                </label>
                <textarea
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  rows={4}
                  placeholder="Write your message here."
                  className="w-full resize-none bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex gap-3 pt-1">
              <button
                onClick={() => setShowNewModal(false)}
                className="flex-1 py-2.5 rounded-xl border border-slate-200 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateThread}
                disabled={creatingThread || !newSubject.trim() || !newMessage.trim()}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold transition-colors"
              >
                {creatingThread ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Send size={14} />
                )}
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

