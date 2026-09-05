'use client';
import { useState } from 'react';
import useSWR from 'swr';
import { fetcher, getHeaders } from '@/api';
import { Star, AlertCircle, Loader2, CheckCircle } from 'lucide-react';

interface Visit {
  appointment_id: string;
  scheduled_time: string;
  department: string;
  doctor_id: string;
  has_review: boolean;
}

interface Review {
  review_id: string;
  appointment_id: string;
  rating: number;
  comment?: string;
  wait_time_rating?: number;
  created_at: string;
}

interface ReviewsData {
  pending_visits: Visit[];
  submitted_reviews: Review[];
}

function StarRating({
  value,
  onChange,
  readonly,
}: {
  value: number;
  onChange?: (v: number) => void;
  readonly?: boolean;
}) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          disabled={readonly}
          onClick={() => onChange?.(n)}
          className={`transition-colors ${readonly ? 'cursor-default' : 'hover:scale-110'}`}
        >
          <Star
            size={20}
            className={n <= value ? 'text-yellow-400 fill-yellow-400' : 'text-slate-300'}
          />
        </button>
      ))}
    </div>
  );
}

function PendingReviewCard({
  visit,
  onSubmit,
}: {
  visit: Visit;
  onSubmit: () => void;
}) {
  const [rating, setRating] = useState(0);
  const [waitRating, setWaitRating] = useState(0);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async () => {
    if (rating === 0) return;
    setSubmitting(true);
    try {
      const res = await fetch('http://localhost:8000/api/reviews/', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          appointment_id: visit.appointment_id,
          rating,
          comment: comment || undefined,
          wait_time_rating: waitRating || undefined,
        }),
      });
      if (res.ok) {
        setDone(true);
        onSubmit();
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (done)
    return (
      <div className="bg-green-50 border border-green-200 rounded-2xl p-6 flex items-center gap-3">
        <CheckCircle size={20} className="text-green-600 shrink-0" />
        <p className="text-sm font-medium text-green-700">Review submitted — thank you!</p>
      </div>
    );

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {new Date(visit.scheduled_time).toLocaleDateString(undefined, {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </span>
          <span className="text-slate-300">Â·</span>
          <span className="text-xs text-slate-500">{visit.department}</span>
        </div>
        <h3 className="text-base font-bold text-slate-800 mt-0.5">
          Dr. {visit.doctor_id}
        </h3>
        <div className="mt-1 inline-block bg-blue-50 border border-blue-100 text-blue-700 text-xs font-semibold px-2.5 py-0.5 rounded-full">
          Leave a Review
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-600 uppercase mb-2">Overall Rating *</label>
          <StarRating value={rating} onChange={setRating} />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 uppercase mb-2">Wait Time Rating</label>
          <StarRating value={waitRating} onChange={setWaitRating} />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 uppercase mb-1.5">Comment (optional)</label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
            placeholder="Share your experience…"
            className="w-full resize-none bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={submitting || rating === 0}
        className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold transition-colors"
      >
        {submitting ? <Loader2 size={14} className="animate-spin" /> : <Star size={14} />}
        {submitting ? 'Submitting…' : 'Submit Review'}
      </button>
    </div>
  );
}

export default function ReviewsPage() {
  const { data, error, isLoading, mutate } = useSWR<ReviewsData>('/reviews/my', fetcher);

  if (isLoading)
    return (
      <div className="max-w-2xl mx-auto grid grid-cols-1 gap-4">
        {[...Array(2)].map((_, i) => (
          <div key={i} className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse space-y-3">
            <div className="h-4 bg-slate-200 rounded w-1/3" />
            <div className="h-3 bg-slate-200 rounded w-1/4" />
            <div className="h-3 bg-slate-200 rounded w-2/3" />
          </div>
        ))}
      </div>
    );

  if (error)
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-6 flex items-center gap-3">
          <AlertCircle size={20} className="shrink-0" />
          <p className="text-sm font-medium">Failed to load reviews. Please try again.</p>
        </div>
      </div>
    );

  const pending = data?.pending_visits ?? [];
  const submitted = data?.submitted_reviews ?? [];

  if (pending.length === 0 && submitted.length === 0)
    return (
      <div className="max-w-2xl mx-auto flex flex-col items-center justify-center py-24 gap-4 text-center">
        <div className="bg-slate-100 rounded-full p-6">
          <Star size={40} className="text-slate-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-700">Complete a visit to leave a review</h2>
        <p className="text-slate-500 text-sm max-w-xs">
          After your appointment, you can rate your experience here.
        </p>
      </div>
    );

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Reviews</h1>
        <p className="text-slate-500 text-sm mt-1">Rate your care experience</p>
      </div>

      {pending.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-slate-700">Awaiting Your Review</h2>
          {pending.map((visit) => (
            <PendingReviewCard key={visit.appointment_id} visit={visit} onSubmit={() => mutate()} />
          ))}
        </div>
      )}

      {submitted.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-slate-700">Your Past Reviews</h2>
          {submitted.map((rev) => (
            <div key={rev.review_id} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <StarRating value={rev.rating} readonly />
                <span className="text-xs text-slate-400">
                  {new Date(rev.created_at).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
              </div>
              {rev.wait_time_rating ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-medium">Wait time:</span>
                  <StarRating value={rev.wait_time_rating} readonly />
                </div>
              ) : null}
              {rev.comment && (
                <p className="text-sm text-slate-600 bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 leading-relaxed">
                  {rev.comment}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

