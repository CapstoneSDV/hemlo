"""
Helper script called by Next.js API route to execute the pipeline.
Usage:
  python api_runner.py stages <scenario_id>
  python api_runner.py paths <before_file> <after_file> [roles_file]
"""
import sys, json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from pipeline_gui import server

def main():
    action = sys.argv[1]
    try:
        if action == 'stages':
            scenario_id = sys.argv[2]
            data = server.run_pipeline_stages(scenario_id)
        elif action == 'paths':
            bef = sys.argv[2]
            aft = sys.argv[3]
            roles = sys.argv[4] if len(sys.argv) > 4 else None
            data = server.run_pipeline_paths(bef, aft, roles)
            data['scenario_id'] = 'custom_upload'
        else:
            data = {'error': f'Unknown action: {action}'}

        print('___JSON_START___')
        print(json.dumps(data))
        print('___JSON_END___')
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print('___JSON_START___')
        print(json.dumps({'error': str(e)}))
        print('___JSON_END___')

if __name__ == '__main__':
    main()
