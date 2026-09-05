'use client';
import useSWR from 'swr';
import { fetcher } from '../../api';

export default function AdminDashboard() {
  const { data: logs } = useSWR('/admin/logs?limit=50', fetcher, { refreshInterval: 5000 });

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Admin Dashboard</h1>

      <div className="bg-white rounded shadow overflow-hidden">
        <div className="px-4 py-5 sm:px-6 bg-gray-50 border-b border-gray-200">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Recent System Logs</h3>
        </div>
        <ul className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
          {logs?.map((log: any, i: number) => (
            <li key={i} className="px-4 py-4 sm:px-6 hover:bg-gray-50">
              <div className="flex justify-between">
                <p className="text-sm font-medium text-blue-600 truncate">{log.event_type || log.message}</p>
                <div className="ml-2 flex-shrink-0 flex">
                  <p className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
              <div className="mt-2 text-sm text-gray-500">
                <pre className="text-xs bg-gray-100 p-2 rounded">{JSON.stringify(log, null, 2)}</pre>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
