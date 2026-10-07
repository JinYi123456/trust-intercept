import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/client.js";
import { cx } from "../lib/ui";

/**
 * Coach — Module 4, the Adaptive Awareness Coach. Turns the just-seen real
 * scam pattern into a short 3–4 question interactive simulation with
 * immediate feedback, reinforcing recognition rather than just delivering a
 * verdict.
 */
export default function Coach() {
  const { caseId } = useParams();
  const [quiz, setQuiz] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .launchCoach(caseId)
      .then((data) => {
        if (active) setQuiz(data);
      })
      .catch((quizError) => {
        if (active) setError(quizError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  function reset() {
    setIndex(0);
    setSelected(null);
    setAnswers([]);
    setFinished(false);
  }

  if (loading) {
    return (
      <div className="py-16 text-center">
        <span className="animate-pulse-glow font-mono text-xs tracking-[0.3em] text-neon-cyan">
          BUILDING YOUR QUIZ FROM THE DETECTED PATTERN…
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl">
        <div role="alert" className="glass-panel border-neon-red/40 p-4 text-sm text-red-200">
          {error}
        </div>
        <Link to={`/case/${caseId}/review`} className="mt-4 inline-block font-mono text-xs tracking-wider text-neon-cyan hover:underline">
          ← BACK TO REVIEW
        </Link>
      </div>
    );
  }

  if (!quiz || !quiz.questions?.length) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="glass-panel border-gold-neon/50 p-4 text-sm text-amber-100">
          No quiz could be generated for this case yet. Run an investigation first, then come back.
        </div>
        <Link to={`/case/${caseId}/review`} className="mt-4 inline-block font-mono text-xs tracking-wider text-neon-cyan hover:underline">
          ← BACK TO REVIEW
        </Link>
      </div>
    );
  }

  const questions = quiz.questions;
  const total = questions.length;

  /* ---------- Results screen ---------- */
  if (finished) {
    const score = answers.filter((answer) => answer.correct).length;
    const missed = answers.filter((answer) => !answer.correct);
    const message =
      score === total
        ? "Excellent — you spotted every red flag."
        : score >= Math.ceil(total / 2)
        ? "Solid recognition — review the misses below."
        : "Good start — this pattern is worth another look.";

    return (
      <div className="mx-auto max-w-2xl">
        <div className="glass-panel p-6 text-center sm:p-8">
          <p className="text-5xl" aria-hidden="true">
            {score === total ? "🛡️" : score >= Math.ceil(total / 2) ? "👏" : "📚"}
          </p>
          <h1 className="mt-3 text-2xl font-black text-slate-100">
            You scored <span className="neon-cyan-text">{score} / {total}</span>
          </h1>
          <p className="mt-2 text-sm text-slate-400">{message}</p>
          <p className="mt-1 font-mono text-xs tracking-wider text-slate-500">
            PATTERN TRAINED: <span className="text-neon-cyan">{quiz.pattern_name}</span>
          </p>

          {missed.length > 0 && (
            <div className="mt-6 space-y-3 text-left">
              <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                REVIEW YOUR MISSES
              </p>
              {missed.map((answer, answerIndex) => {
                const question = questions[answer.questionIndex];
                return (
                  <div key={answerIndex} className="rounded-lg border border-slate-800 bg-space-950/70 p-3">
                    <p className="text-sm font-medium text-slate-200">{question.question}</p>
                    <p className="mt-1 text-sm text-neon-green">
                      Correct answer: {question.options[question.correct_index]}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">{question.explanation}</p>
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-8 flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={reset}
              className="flex-1 rounded-xl border border-slate-700 bg-space-900/70 px-4 py-3 font-mono text-sm font-bold tracking-wider text-slate-300 transition hover:border-neon-cyan/40 hover:text-neon-cyan"
            >
              RETAKE QUIZ
            </button>
            <Link
              to={`/case/${caseId}/review`}
              className="flex-1 rounded-xl border border-slate-700 bg-space-900/70 px-4 py-3 text-center font-mono text-sm font-bold tracking-wider text-slate-300 transition hover:border-neon-cyan/40 hover:text-neon-cyan"
            >
              BACK TO REVIEW
            </Link>
            <Link
              to="/"
              className="flex-1 rounded-xl border border-neon-cyan/60 bg-neon-cyan/15 px-4 py-3 text-center font-mono text-sm font-black tracking-wider text-neon-cyan shadow-glow-cyan-soft transition hover:bg-neon-cyan/25"
            >
              SUBMIT ANOTHER CASE
            </Link>
          </div>
        </div>
      </div>
    );
  }

  /* ---------- Quiz screen ---------- */
  const question = questions[index];
  const answered = selected !== null;
  const isCorrect = selected === question.correct_index;

  function handleNext() {
    const answer = { questionIndex: index, selected, correct: selected === question.correct_index };
    const nextAnswers = [...answers, answer];
    setAnswers(nextAnswers);
    if (index + 1 >= total) {
      setFinished(true);
    } else {
      setIndex(index + 1);
      setSelected(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 text-center">
        <span className="glass-sub inline-flex items-center rounded-full px-3 py-1 font-mono text-[11px] font-bold tracking-wider text-neon-cyan">
          PATTERN: {quiz.pattern_name}
        </span>
        {quiz.generated_by_llm && (
          <span className="ml-2 inline-flex items-center rounded-full border border-neon-cyan/40 bg-neon-cyan/10 px-3 py-1 font-mono text-[11px] tracking-wider text-neon-cyan">
            GENERATED FROM YOUR REAL CASE
          </span>
        )}
        <h1 className="mt-3 text-2xl font-black text-slate-100">Quick awareness check</h1>
        <p className="mt-1 font-mono text-xs tracking-wider text-slate-500">
          QUESTION {index + 1} OF {total}
        </p>
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-space-800">
          <div
            className="h-full rounded-full bg-neon-cyan shadow-glow-cyan-soft transition-all"
            style={{ width: `${((index + (answered ? 1 : 0)) / total) * 100}%` }}
          />
        </div>
      </div>

      <div className="glass-panel p-5 sm:p-6">
        <p className="text-base font-semibold text-slate-100 sm:text-lg">{question.question}</p>

        <div className="mt-4 space-y-2">
          {question.options.map((option, optionIndex) => {
            const isSelected = selected === optionIndex;
            const isAnswer = optionIndex === question.correct_index;
            let style = "border-slate-700 bg-space-950/70 hover:border-neon-cyan/50 hover:bg-neon-cyan/5";
            if (answered && isAnswer) {
              style = "border-neon-green/70 bg-neon-green/10 ring-1 ring-neon-green/50";
            } else if (answered && isSelected && !isAnswer) {
              style = "border-neon-red/70 bg-neon-red/10 ring-1 ring-neon-red/40";
            } else if (answered) {
              style = "border-slate-800 bg-space-950/70 opacity-50";
            }
            return (
              <button
                key={optionIndex}
                type="button"
                disabled={answered}
                onClick={() => setSelected(optionIndex)}
                className={cx(
                  "flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left text-sm transition",
                  style
                )}
              >
                <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full border border-slate-600 font-mono text-[10px] font-bold text-slate-400">
                  {String.fromCharCode(65 + optionIndex)}
                </span>
                <span className="text-slate-200">{option}</span>
                {answered && isAnswer && (
                  <span className="ml-auto shrink-0 font-mono text-xs font-bold text-neon-green">✓ CORRECT</span>
                )}
                {answered && isSelected && !isAnswer && (
                  <span className="ml-auto shrink-0 font-mono text-xs font-bold text-neon-red">✗ YOUR PICK</span>
                )}
              </button>
            );
          })}
        </div>

        {answered && (
          <div
            className={cx(
              "mt-4 rounded-lg border p-4 text-sm",
              isCorrect
                ? "border-neon-green/50 bg-neon-green/10 text-emerald-100"
                : "border-gold-neon/50 bg-gold-neon/10 text-amber-100"
            )}
          >
            <p className="font-bold">{isCorrect ? "Correct!" : "Not quite — here's why:"}</p>
            <p className="mt-1">{question.explanation}</p>
          </div>
        )}

        <div className="mt-5 flex justify-end">
          <button
            type="button"
            disabled={!answered}
            onClick={handleNext}
            className={cx(
              "rounded-xl px-6 py-3 font-mono text-sm font-black tracking-wider transition",
              answered
                ? "border border-neon-cyan/60 bg-neon-cyan/15 text-neon-cyan shadow-glow-cyan-soft hover:bg-neon-cyan/25"
                : "cursor-not-allowed border border-slate-800 bg-space-950 text-slate-600"
            )}
          >
            {index + 1 >= total ? "SEE MY SCORE" : "NEXT QUESTION →"}
          </button>
        </div>
      </div>

      <p className="mt-4 text-center font-mono text-[11px] tracking-wider text-slate-500">
        This quiz is a reinforcement aid built from the pattern just detected — not a certified
        training curriculum.
      </p>
    </div>
  );
}
