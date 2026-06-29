import type { DocumentVersionChainState, DocumentVersionNode } from "./selectors";

export interface DocumentVersionsTabProps {
  chain: DocumentVersionChainState;
}

export function DocumentVersionsTab({ chain }: DocumentVersionsTabProps) {
  return (
    <section className="document-panel document-versions" aria-labelledby="document-versions-title">
      <div className="document-panel-heading">
        <div>
          <p className="section-eyebrow">版本</p>
          <h3 id="document-versions-title">版本链路</h3>
          <p>{chain.conclusion}</p>
        </div>
      </div>

      <p className="document-version-chain-label">内部初稿 -&gt; 质量检查 -&gt; 正式稿 -&gt; 成稿会审 -&gt; 导出</p>

      <ol className="document-version-chain">
        {chain.nodes.map((node) => (
          <VersionNodeView node={node} key={node.id} />
        ))}
      </ol>
    </section>
  );
}

function VersionNodeView({ node }: { node: DocumentVersionNode }) {
  return (
    <li className="document-version-node">
      <div className="document-version-node-heading">
        <div>
          <strong>{node.label}</strong>
          <small>{node.timeLabel}</small>
        </div>
        <span className="document-state-pill">{node.state}</span>
      </div>
      <p>{node.detail}</p>
      {node.shortHash ? <span className="document-short-hash">短标识 {node.shortHash}</span> : null}
      {node.fullHashes.length > 0 ? (
        <details className="document-version-details">
          <summary>查看哈希详情</summary>
          <dl>
            {node.fullHashes.map((hash) => (
              <div key={hash.label}>
                <dt>{hash.label}</dt>
                <dd>{hash.value}</dd>
              </div>
            ))}
          </dl>
        </details>
      ) : null}
    </li>
  );
}
