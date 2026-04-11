import type { ActionItem } from "@/services/api";

type ActionItemsListProps = {
  action_items: ActionItem[];
};

export function ActionItemsList({ action_items }: ActionItemsListProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
          Action Items
        </p>
        <h2 className="mt-1 text-lg font-semibold text-slate-900">What needs follow-up</h2>
      </div>

      {action_items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5">
          <p className="text-sm text-slate-500">No action items were extracted yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {action_items.map((item, index) => (
            <div
              key={`${item.task}-${index}`}
              className="rounded-2xl border border-slate-100 bg-slate-50 p-4"
            >
              <p className="font-medium text-slate-900">{item.task}</p>
              <div className="mt-2 flex flex-wrap gap-2 text-sm text-slate-500">
                <span className="rounded-full bg-white px-3 py-1">
                  Owner: {item.assigned_to || "Unassigned"}
                </span>
                {item.deadline ? (
                  <span className="rounded-full bg-white px-3 py-1">
                    Deadline: {item.deadline}
                  </span>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
