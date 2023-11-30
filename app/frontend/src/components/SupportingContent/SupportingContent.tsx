import { parseSupportingContentItem } from "./SupportingContentParser";

import styles from "./SupportingContent.module.css";

interface Props {
    supportingContent: string[];
}

export const SupportingContent = ({ supportingContent }: Props) => {
    return (
        <ul className={styles.supportingContentNavList}>
            {supportingContent.map((x, i) => {
                const parsed = parseSupportingContentItem(x);

                return (
                    <li className={styles.supportingContentItem} key={`supporting-content-${i}`}>
                        <div className={styles.supportingContentItemHeader}>
                            <h5 className={styles.supportingContentItemHeaderText}>{`${parsed.id}`}</h5>
                            <h5 className={styles.supportingContentItemHeaderText}>{`score: ${parsed.score}`}</h5>
                        </div>
                        <h5 className={styles.supportingContentItemCategory}>{`${parsed.category}`}</h5>
                        <p className={styles.supportingContentItemText}>{parsed.content}</p>
                    </li>
                );
            })}
        </ul>
    );
};
